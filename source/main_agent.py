import os
import json
from datetime import datetime
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, ToolMessage

from source.utils import _clean_response
from source.base import SearchAgentInput
from source.search_agent import search_agent
from source.prompts import MAIN_AGENT_SYSTEM_PROMPT, MAIN_AGENT_PROMPT

def call_search_agent(query: str):

    # Call search agent
    messages = [HumanMessage(content=query)]
    result = search_agent.invoke({"messages": messages})


    # Parse response
    last_response = result['messages'][-1].content
    if last_response.lower() == "complete":

        try:

            if isinstance(result['messages'][-2], ToolMessage):
                tool_response = json.loads(result['messages'][-2].content)
                cache_key = tool_response['cache_key']

                path = os.path.join('cache', f'{cache_key}.json')
                with open(path, mode='r', encoding='utf-8') as file:
                    data = json.load(file)

                # Summarize                    
                flights = _clean_response(data)
                if not flights:
                    return "No flights found"

                prices = [f["price"] for f in flights]
                airlines = list(set(
                    seg["airline"]
                    for f in flights
                    for seg in f.get("segments", [])
                ))
                durations = [f["total_duration"] for f in flights]

                summary = {
                    "found": len(flights),
                    "price_min": min(prices),
                    "price_max": max(prices),
                    "currency": data.get("search_parameters", {}).get("currency", "VND"),
                    "airlines": airlines,
                    "duration_min": min(durations),
                    "duration_max": max(durations),
                    "cache_key": cache_key
                }
                return summary         

            else:
                print(result)
                raise 'Unexpected error'

        except Exception as e:
            raise e

    return last_response

call_search_agent_tool = StructuredTool.from_function(
    func=call_search_agent,
    name="search_flights",
    description=(
        "Search for actual flight tickets. "
        "CRITICAL: Do NOT call this tool for general questions, greetings, or to explain your capabilities. "
        "ONLY call this tool when you have a specific Origin, Destination, and Date to search for."
    ),
    args_schema=SearchAgentInput,
)

main_agent_model = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    reasoning_effort='medium'
)

main_agent = create_react_agent(
    model=main_agent_model,
    tools=[call_search_agent_tool],
    prompt=MAIN_AGENT_PROMPT.format(
        current_date=str(datetime.today().date())
    )
)
