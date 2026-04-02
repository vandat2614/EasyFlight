import os
import json
import time
import requests

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage

from source.base import ChatRequest
from source.main_agent import main_agent
from source.utils import _clean_response

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Flight Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


def _build_messages(req: ChatRequest):
    messages = []
    for msg in req.history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=req.message))
    return messages


async def _stream_agent(req: ChatRequest):
    """
    SSE stream format:
      event: token          -> each text token from main agent
      event: searching      -> tool call started (search in progress)
      event: searching_done -> tool call ended
      event: flights        -> JSON flight list (at the end)
      event: done           -> stream finished
    """
    messages = _build_messages(req)
    start_time = time.time()

    async for event in main_agent.astream_events(
        {"messages": messages}, version="v2"
    ):
        kind = event["event"]

        # Main agent called tool -> searching animation
        if kind == "on_tool_start":
            ns = event["metadata"].get("langgraph_checkpoint_ns", "")
            if "|" not in ns:
                yield f"event: searching\ndata: {{}}\n\n"

        # Tool finished -> stop searching animation
        elif kind == "on_tool_end":
            ns = event["metadata"].get("langgraph_checkpoint_ns", "")
            if "|" not in ns:
                yield f"event: searching_done\ndata: {{}}\n\n"

        # Stream each token from main agent only
        elif kind == "on_chat_model_stream":
            meta = event["metadata"]
            ns = meta.get("langgraph_checkpoint_ns", "")
            if meta.get("langgraph_node") == "agent" and "|" not in ns:
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield f"event: token\ndata: {json.dumps(chunk.content, ensure_ascii=False)}\n\n"

    # After stream ends, check cache folder for files created during the stream
    flights = []
    cache_dir = "cache"
    if os.path.exists(cache_dir):
        for fname in os.listdir(cache_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(cache_dir, fname)
            if os.path.getmtime(fpath) >= start_time:
                with open(fpath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                flights = _clean_response(raw)
                search_params = raw.get("search_parameters", {})
                break

    if flights:
        payload = {
            "flights": flights,
            "search_params": {
                "departure_id": search_params.get("departure_id", ""),
                "arrival_id": search_params.get("arrival_id", ""),
                "outbound_date": search_params.get("outbound_date", ""),
                "type": int(search_params.get("type", 2)),
                "currency": search_params.get("currency", "VND"),
            },
        }
        yield f"event: flights\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    yield f"event: done\ndata: {{}}\n\n"


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        _stream_agent(req),
        media_type="text/event-stream",
    )


class BookingRequest(BaseModel):
    booking_token: str
    departure_id: str
    arrival_id: str
    outbound_date: str
    type: int = 2
    currency: str = "VND"
    gl: str = "vn"
    hl: str = "vi"


@app.post("/booking")
async def get_booking(req: BookingRequest):
    params = {
        "engine": "google_flights",
        "departure_id": req.departure_id,
        "arrival_id": req.arrival_id,
        "outbound_date": req.outbound_date,
        "type": req.type,
        "booking_token": req.booking_token,
        "currency": req.currency,
        "gl": req.gl,
        "hl": req.hl,
        "api_key": os.environ["SERP_API_KEY"],
    }
    res = requests.get("https://serpapi.com/search", params=params)
    data = res.json()
    options = data.get("booking_options", [])

    results = []
    for opt in options:
        info = opt.get("together", opt)
        booking_req = info.get("booking_request", {})
        results.append({
            "provider": info.get("book_with", ""),
            "price": info.get("price"),
            "url": booking_req.get("url", ""),
            "post_data": booking_req.get("post_data", ""),
            "logos": info.get("airline_logos", []),
        })
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("source.app:app", host="0.0.0.0", port=8001, reload=True)
