import os
from datetime import datetime
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool
from source.tools import search_flights_wrapper
from source.base import SearchFlightsInput
from source.prompts import SEARCH_AGENT_SYSTEM_PROMPT
from dotenv import load_dotenv

MODEL_NAME = "openai/gpt-oss-120b"
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


search_agent_model = ChatGroq(
    model=MODEL_NAME,
    temperature=0,
    reasoning_effort='low'
)

search_flights_tool = StructuredTool.from_function(
    func=search_flights_wrapper,
    name="search_flights",
    description="Search for available flights and real-time ticket prices between airports worldwide.",
    args_schema=SearchFlightsInput,
)

search_agent = create_react_agent(
    model=search_agent_model,
    tools=[search_flights_tool],
    prompt=SEARCH_AGENT_SYSTEM_PROMPT.format(
        current_date=str(datetime.today().date())
    )
)