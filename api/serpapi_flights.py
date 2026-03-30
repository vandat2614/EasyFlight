"""
Google Flights Search API wrapper (via SerpApi).

Provides search_flights() to search for flights and real-time ticket prices
from Google Flights. Supports local file caching of raw responses to save
API calls.

Setup:
    1. Sign up at https://serpapi.com -> get API key
    2. Create .env file: SERPAPI_KEY=your_key
    3. pip install requests python-dotenv

Usage:
    from flight_search import search_flights, print_flights

    data = search_flights(
        departure_id="SGN",
        arrival_id="HAN",
        outbound_date="2026-04-15",
    )
    print_flights(data)
"""

import hashlib
import io
import sys
import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Fix Windows console encoding (cp1252 can't print Unicode characters)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv()

_SERPAPI_KEY = os.getenv("SERPAPI_KEY")
_BASE_URL = "https://serpapi.com/search"
_CACHE_DIR = Path(__file__).parent.parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_key(params: dict) -> str:
    """Generate an MD5 hash from query params (excluding api_key) to use as cache filename."""
    filtered = {k: v for k, v in sorted(params.items()) if k != "api_key"}
    raw = json.dumps(filtered, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _load_cache(key: str) -> dict | None:
    """Load cached raw response from file. Returns None if cache miss."""
    path = _CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        cached = json.load(f)
    print(f"  [CACHE HIT] {path.name} (saved at {cached['cached_at']})")
    return cached["response"]


def _save_cache(key: str, params: dict, raw_response: dict) -> None:
    """Save raw API response to a JSON cache file."""
    path = _CACHE_DIR / f"{key}.json"
    cached = {
        "cached_at": datetime.now().isoformat(),
        "params": {k: v for k, v in params.items() if k != "api_key"},
        "response": raw_response,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cached, f, ensure_ascii=False, indent=2)
    print(f"  [CACHED] -> {path.name}")


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def search_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str | None = None,
    # -- Trip type --
    trip_type: int | None = None,
    multi_city_json: str | None = None,
    # -- Passengers --
    adults: int = 1,
    children: int = 0,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    # -- Cabin class --
    travel_class: int = 1,
    # -- Filters --
    stops: int = 0,
    max_price: int | None = None,
    max_duration: int | None = None,
    bags: int = 0,
    include_airlines: str | None = None,
    exclude_airlines: str | None = None,
    outbound_times: str | None = None,
    return_times: str | None = None,
    layover_duration: str | None = None,
    exclude_conns: str | None = None,
    emissions: int | None = None,
    # -- Display & sorting --
    sort_by: int = 1,
    currency: str = "VND",
    gl: str = "vn",
    hl: str = "vi",
    show_hidden: bool = False,
    deep_search: bool = False,
    # -- Token (multi-step flow) --
    departure_token: str | None = None,
    booking_token: str | None = None,
    # -- Cache & SerpApi control --
    use_cache: bool = True,
    no_cache: bool = False,
    api_key: str | None = None,
) -> dict | None:
    """Search for flights and real-time ticket prices from Google Flights.

    Args:
        departure_id:
            Departure airport IATA code (3 letters) or location kgmid (starting with /m/).
            Supports multiple airports separated by comma.
            Examples: "SGN", "SGN,BMV", "/m/0fnff3"

        arrival_id:
            Arrival airport. Same format as departure_id.
            Examples: "HAN", "HAN,HPH"

        outbound_date:
            Departure date in YYYY-MM-DD format.
            Example: "2026-04-15"

        return_date:
            Return date (required for round trips). YYYY-MM-DD format.
            Defaults to None (one-way).
            Example: "2026-04-20"

        trip_type:
            Flight type. Auto-detected from return_date if not set.
            - 1: Round trip
            - 2: One way
            - 3: Multi-city (requires multi_city_json)

        multi_city_json:
            JSON string for multi-city flights (when trip_type=3).
            Example: '[{"departure_id":"SGN","arrival_id":"HAN","date":"2026-04-15"},
                       {"departure_id":"HAN","arrival_id":"DAD","date":"2026-04-18"}]'

        adults:
            Number of adult passengers. Defaults to 1.

        children:
            Number of child passengers. Defaults to 0.

        infants_in_seat:
            Number of infants with their own seat. Defaults to 0.

        infants_on_lap:
            Number of infants sitting on lap. Defaults to 0.

        travel_class:
            Cabin class:
            - 1: Economy (default)
            - 2: Premium Economy
            - 3: Business
            - 4: First

        stops:
            Maximum number of stops:
            - 0: Any number of stops (default)
            - 1: Nonstop only
            - 2: 1 stop or fewer
            - 3: 2 stops or fewer

        max_price:
            Maximum ticket price in the specified currency. None = no limit.
            Example: 5000000 (5 million VND)

        max_duration:
            Maximum total flight duration in minutes. None = no limit.
            Example: 300 (5 hours)

        bags:
            Number of carry-on bags. Defaults to 0.

        include_airlines:
            Only show flights from these airlines. Comma-separated IATA codes.
            Cannot be used together with exclude_airlines.
            Example: "VN,VJ,QH" (Vietnam Airlines, VietJet, Bamboo Airways)
            Supports alliances: "STAR_ALLIANCE", "SKYTEAM", "ONEWORLD"

        exclude_airlines:
            Exclude flights from these airlines. Same format as include_airlines.
            Cannot be used together with include_airlines.

        outbound_times:
            Outbound departure time range. 2 or 4 comma-separated hours.
            Example: "6,18" (departures between 6:00-18:00 only)
            Example: "6,18,3,19" (depart 6-18h, arrive 3-19h)

        return_times:
            Return departure time range. Same format as outbound_times.
            Only used when trip_type=1 (round trip).

        layover_duration:
            Layover duration range as min,max in minutes.
            Example: "90,330" (1.5 hours to 5.5 hours)

        exclude_conns:
            Exclude connecting airports. Comma-separated IATA codes.
            Example: "ICN,NRT" (no connections through Seoul or Tokyo)

        emissions:
            Filter by carbon emissions:
            - None: No filter (default)
            - 1: Less emissions only

        sort_by:
            Sort results by:
            - 1: Top flights - best overall (default)
            - 2: Price - lowest first
            - 3: Departure time
            - 4: Arrival time
            - 5: Duration - shortest first
            - 6: Emissions - lowest CO2 first

        currency:
            Currency code for prices. Defaults to "VND".
            Examples: "VND", "USD", "EUR", "JPY"

        gl:
            Country code (2 letters) for localized results. Defaults to "vn".
            Examples: "vn", "us", "jp"

        hl:
            Language code (2 letters). Defaults to "vi".
            Examples: "vi", "en", "ja"

        show_hidden:
            Include hidden flight results. Defaults to False.

        deep_search:
            Return results identical to Google Flights in browser. Defaults to False.
            Note: slower and may consume more API credits.

        departure_token:
            Token to retrieve return flights (round trip) or next leg (multi-city).
            Obtained from previous search response (departure_token field in each flight).
            Cannot be used together with booking_token.

        booking_token:
            Token to retrieve booking options for a selected flight.
            Obtained from previous search response (booking_token field in each flight).
            Cannot be used together with departure_token.

        use_cache:
            Use local file cache. Defaults to True.
            Set to False to always call the API (still saves to cache).

        no_cache:
            Bypass SerpApi server-side cache. Defaults to False.
            Set to True to always get fresh data from Google Flights.

        api_key:
            SerpApi API key. Defaults to SERPAPI_KEY from .env.
            Pass directly to override the environment variable.

    Returns:
        dict: Raw JSON response from SerpApi. Main structure:
            - search_metadata: Request info (id, status, timing)
            - search_parameters: Parameters sent to the API
            - price_insights: {lowest_price, typical_price_range, price_level, price_history}
            - best_flights: List of best flight offers
            - other_flights: List of other flight offers
            - airports: Airport information
            Each flight contains: price, total_duration, flights (segments), layovers,
            departure_token, booking_token, carbon_emissions, airline_logos, etc.
        None: If an error occurs.

    Examples:
        # One-way SGN -> HAN
        data = search_flights("SGN", "HAN", "2026-04-15")

        # Round trip, Business class
        data = search_flights(
            "SGN", "HAN", "2026-04-15",
            return_date="2026-04-20",
            travel_class=3,
        )

        # Vietnam Airlines and VietJet only, nonstop, max price 3 million VND
        data = search_flights(
            "SGN", "HAN", "2026-04-15",
            include_airlines="VN,VJ",
            stops=1,
            max_price=3000000,
        )

        # Price in USD, sorted by price
        data = search_flights(
            "SGN", "NRT", "2026-05-01",
            currency="USD",
            sort_by=2,
        )
    """
    key_to_use = api_key or _SERPAPI_KEY
    if not key_to_use:
        print("Error: Missing SERPAPI_KEY. Set it in .env or pass api_key=...")
        return None

    # Auto-detect trip type from return_date if not explicitly set
    if trip_type is None:
        trip_type = 2 if return_date is None else 1

    # --- Build required params ---
    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "type": trip_type,
        "adults": adults,
        "travel_class": travel_class,
        "stops": stops,
        "sort_by": sort_by,
        "currency": currency,
        "gl": gl,
        "hl": hl,
        "api_key": key_to_use,
    }

    # --- Add optional params (only when set) ---
    optional = {
        "return_date": return_date,
        "multi_city_json": multi_city_json,
        "children": children or None,
        "infants_in_seat": infants_in_seat or None,
        "infants_on_lap": infants_on_lap or None,
        "max_price": max_price,
        "max_duration": max_duration,
        "bags": bags or None,
        "include_airlines": include_airlines,
        "exclude_airlines": exclude_airlines,
        "outbound_times": outbound_times,
        "return_times": return_times,
        "layover_duration": layover_duration,
        "exclude_conns": exclude_conns,
        "emissions": emissions,
        "departure_token": departure_token,
        "booking_token": booking_token,
    }
    for k, v in optional.items():
        if v is not None:
            params[k] = v

    # Boolean flags (only send when True)
    if show_hidden:
        params["show_hidden"] = "true"
    if deep_search:
        params["deep_search"] = "true"
    if no_cache:
        params["no_cache"] = "true"

    # --- Check local cache ---
    cache_key = _cache_key(params)
    if use_cache:
        data = _load_cache(cache_key)
        if data is not None:
            return data

    # --- Call API ---
    print(f"  [API CALL] {departure_id}->{arrival_id} {outbound_date}")
    response = requests.get(_BASE_URL, params=params)
    data = response.json()

    if "error" in data:
        print(f"  [ERROR] {data['error']}")
        return None

    # --- Save raw response to cache ---
    _save_cache(cache_key, params, data)

    return data


# ---------------------------------------------------------------------------
# Display helper
# ---------------------------------------------------------------------------

def print_flights(data: dict, currency: str = "VND") -> None:
    """Print flight search results in a human-readable format.

    Args:
        data: Raw response dict from search_flights().
        currency: Currency label for display. Defaults to "VND".
    """
    if not data:
        print("No data available.")
        return

    # Extract search params from response for header
    params = data.get("search_parameters", {})
    origin = params.get("departure_id", "?")
    dest = params.get("arrival_id", "?")
    date = params.get("outbound_date", "?")
    ret = params.get("return_date")
    trip_type = "Round trip" if ret else "One way"

    print(f"\n{'='*65}")
    print(f"  {origin} -> {dest} | {date} | {trip_type}")
    print(f"{'='*65}")

    # Price insights (lowest price, typical range)
    insights = data.get("price_insights", {})
    if insights:
        lowest = insights.get("lowest_price")
        typical = insights.get("typical_price_range", [])
        if lowest:
            print(f"\n  Lowest price: {lowest:,} {currency}")
        if typical:
            print(f"  Typical range: {typical[0]:,} - {typical[1]:,} {currency}")

    # Combine best and other flights
    best = data.get("best_flights", [])
    other = data.get("other_flights", [])
    all_flights = best + other

    if not all_flights:
        print("\n  No flights found.")
        return

    # Display top 10 results
    for i, flight in enumerate(all_flights[:10], 1):
        price = flight.get("price", "N/A")
        total_duration = flight.get("total_duration", 0)
        hours, mins = divmod(total_duration, 60)

        is_best = i <= len(best)
        tag = " [Best]" if is_best else ""

        print(f"\n--- Flight {i}{tag} ---")
        print(f"  Price: {price:,} {currency}" if isinstance(price, int) else f"  Price: {price} {currency}")
        print(f"  Total duration: {hours}h{mins:02d}m")
        print(f"  Segments: {len(flight.get('flights', []))}")

        # Print each flight segment
        for seg in flight.get("flights", []):
            dep = seg.get("departure_airport", {})
            arr = seg.get("arrival_airport", {})
            airline = seg.get("airline", "")
            flight_no = seg.get("flight_number", "")
            duration = seg.get("duration", 0)
            h, m = divmod(duration, 60)
            print(
                f"    {airline} {flight_no}: "
                f"{dep.get('id', '?')} ({dep.get('time', '')}) -> "
                f"{arr.get('id', '?')} ({arr.get('time', '')}) "
                f"[{h}h{m:02d}m]"
            )

        # Print layover info if any
        for layover in flight.get("layovers", []):
            lo_name = layover.get("name", "")
            lo_dur = layover.get("duration", 0)
            lh, lm = divmod(lo_dur, 60)
            print(f"    -> Layover: {lo_name} ({lh}h{lm:02d}m)")

    print(f"\n=> Total: {len(all_flights)} flights found.\n")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # One-way: Ho Chi Minh -> Ha Noi
    data = search_flights("SGN", "HAN", "2026-04-15", sort_by=2)
    if data:
        print_flights(data)

    # Round trip: Ha Noi -> Da Nang, Business class
    data = search_flights(
        "HAN", "DAD", "2026-04-20",
        return_date="2026-04-25",
        travel_class=3,
        sort_by=2,
    )
    if data:
        print_flights(data)

    # Run again -> uses cache, no API call consumed
    print("\n>>> Running again (will use cache):")
    data = search_flights("SGN", "HAN", "2026-04-15", sort_by=2)
    if data:
        print_flights(data)
