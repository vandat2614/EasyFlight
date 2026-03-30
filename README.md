# Flight Search Agent

Search for flights the way you talk. Just describe your travel plans in natural language—origin, destination, dates, and preferences—and get instant flight options with prices, airlines, and schedules all at once.

## Features

- Chat interface with prompt-driven flight search
- Flight results shown in a dedicated panel with real-time updates
- Get instant pricing and availability across multiple airlines and routes
- Filter by price, duration, stops, airline preferences, and more
- Easy-to-read results panel displaying side-by-side flight comparisons

## Project structure

```
Flight/
├── src/
│   ├── app.py                  # FastAPI server + LangChain agent wiring
│   ├── base.py                 # Pydantic request/response schemas
│   ├── prompt.py               # System prompt template for the agent
│   ├── tools.py                # Flight search wrapper + flight data cleaning
│   └── static/                 # Static frontend assets (HTML/CSS/JS)
├── api/
│   └── serpapi_flights.py      # Flight search API integration
├── .env                        # API key configuration (gitignored)
├── .venv/                      # Python virtual environment
├── README.md
└── requirements.txt
```

## Setup & Run

```powershell
git clone https://github.com/your-username/Flight.git
cd Flight
python -m venv .venv
venv\Scripts\activate          # On Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
SERPAPI_KEY=your_serpapi_api_key
GROQ_API_KEY=your_groq_api_key
```

Get API keys from:
- SerpApi: https://serpapi.com
- Groq: https://console.groq.com

Start the server:

```powershell
python src/app.py
```

Open your browser at `http://127.0.0.1:8000/`

## Tech stack

- Python 3.11+
- FastAPI + Uvicorn
- LangChain + Groq LLM
- SerpApi / Google Flights integration
