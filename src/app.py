import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from base import ChatRequest, ChatResponse, SearchFlightsInput
from prompt import SYSTEM_PROMPT_TEMPLATE
from tools import _search_flights_web

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Init 
# Shared state: last search results for frontend
last_search_result = {"flights": [], "tool_calls": []}

def _search_flights_tool_wrapper(**kwargs):
    return _search_flights_web(last_search_result=last_search_result, **kwargs)

system_prompt = SYSTEM_PROMPT_TEMPLATE.format(today_date=date.today())
search_flights_tool = StructuredTool.from_function(
    func=_search_flights_tool_wrapper,
    name="search_flights",
    description="Search for available flights and real-time ticket prices between airports worldwide.",
    args_schema=SearchFlightsInput,
)

model = ChatGroq(model="openai/gpt-oss-120b",temperature=0,)
agent = create_react_agent(
    model=model,
    tools=[search_flights_tool],
    prompt=system_prompt,
)


# FastAPI

app = FastAPI(title="Flight Search Agent")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    
    # Reset shared state
    last_search_result["flights"] = []
    last_search_result["tool_calls"] = []

    # Build message history
    messages = []
    for msg in req.history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=req.message))

    # Run agent
    result = agent.invoke({"messages": messages})

    final_msg = result["messages"][-1].content
    searched = len(last_search_result["tool_calls"]) > 0

    return ChatResponse(
        response=final_msg,
        flights=last_search_result["flights"],
        tool_calls=last_search_result["tool_calls"],
        searched=searched,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
