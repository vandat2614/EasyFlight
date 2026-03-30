
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.serpapi_flights import search_flights as _search


def _clean_segment(raw: dict) -> dict:
    """Transform a raw flight segment into a clean structure."""
    dep = raw.get("departure_airport", {})
    arr = raw.get("arrival_airport", {})
    return {
        "departure_airport": dep.get("id", ""),
        "departure_airport_name": dep.get("name", ""),
        "departure_time": dep.get("time", ""),
        "arrival_airport": arr.get("id", ""),
        "arrival_airport_name": arr.get("name", ""),
        "arrival_time": arr.get("time", ""),
        "duration": raw.get("duration", 0),
        "airline": raw.get("airline", ""),
        "airline_logo": raw.get("airline_logo", ""),
        "flight_number": raw.get("flight_number", ""),
        "airplane": raw.get("airplane", ""),
        "travel_class": raw.get("travel_class", ""),
        "legroom": raw.get("legroom", ""),
        "amenities": raw.get("extensions", []),
        "overnight": raw.get("overnight", False),
        "often_delayed": raw.get("often_delayed_by_over_30_min", False),
    }


def _clean_layover(raw: dict) -> dict:
    """Transform a raw layover into a clean structure."""
    return {
        "airport": raw.get("id", ""),
        "airport_name": raw.get("name", ""),
        "duration": raw.get("duration", 0),
    }


def _clean_flight(raw: dict) -> dict:
    """Transform a raw flight offer into a clean structure."""
    return {
        "price": raw.get("price", 0),
        "total_duration": raw.get("total_duration", 0),
        "type": raw.get("type", ""),
        "booking_token": raw.get("booking_token", ""),
        "departure_token": raw.get("departure_token", ""),
        "segments": [_clean_segment(s) for s in raw.get("flights", [])],
        "layovers": [_clean_layover(l) for l in raw.get("layovers", [])],
        "carbon_emissions": raw.get("carbon_emissions", {}),
    }


def _clean_response(raw: dict) -> list[dict]:
    """Transform the raw API response into a flat list of flights."""
    best = raw.get("best_flights", [])
    other = raw.get("other_flights", [])
    return [_clean_flight(f) for f in best + other]

def search_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    travel_class: int = 1,
    stops: int = 0,
    max_price: int | None = None,
    max_duration: int | None = None,
    bags: int = 0,
    outbound_times: str | None = None,
    return_times: str | None = None,
    layover_duration: str | None = None,
    exclude_conns: str | None = None,
    sort_by: int = 1,
    currency: str = "VND",
    gl: str = "vn",
    hl: str = "vi",
    show_hidden: bool = False,
    departure_token: str | None = None,
    booking_token: str | None = None,
) -> dict:

    """
    Search Flights Tool

    Search for available flights and real-time ticket prices between airports worldwide.
    Supports one-way and round-trip searches with filters for passengers, cabin class,
    stops, price, duration, time range, layover, and more.

    Input:
        departure_id (str, required):
            Departure airport IATA code (3 letters). Supports multiple airports
            separated by comma.
            Examples: "SGN", "HAN", "SGN,BMV"

        arrival_id (str, required):
            Arrival airport IATA code. Same format as departure_id.
            Examples: "NRT", "DXB", "NRT,HND"

        outbound_date (str, required):
            Departure date in YYYY-MM-DD format.
            Example: "2026-04-15"

        return_date (str, optional):
            Return date in YYYY-MM-DD format. If provided, the search becomes
            a round trip. If omitted, the search is one-way.
            Example: "2026-04-20"

        adults (int, optional):
            Number of adult passengers. Default: 1.

        children (int, optional):
            Number of child passengers. Default: 0.

        infants_in_seat (int, optional):
            Number of infants with their own seat. Default: 0.

        infants_on_lap (int, optional):
            Number of infants sitting on a parent's lap. Default: 0.

        travel_class (int, optional):
            Cabin class:
            - 1: Economy (default)
            - 2: Premium Economy
            - 3: Business
            - 4: First

        stops (int, optional):
            Maximum number of stops:
            - 0: Any number of stops (default)
            - 1: Nonstop only
            - 2: 1 stop or fewer
            - 3: 2 stops or fewer

        max_price (int, optional):
            Maximum ticket price in the specified currency. No limit if omitted.
            Example: 5000000

        max_duration (int, optional):
            Maximum total flight duration in minutes. No limit if omitted.
            Example: 300 (5 hours)

        bags (int, optional):
            Number of checked bags. Default: 0.

        outbound_times (str, optional):
            Outbound departure time range. Comma-separated hours.
            2 values: departure window. 4 values: departure + arrival window.
            Examples: "6,18" (depart 6h-18h), "6,18,8,22" (depart 6-18h, arrive 8-22h)

        return_times (str, optional):
            Return departure time range. Same format as outbound_times.
            Only applies to round-trip searches.

        layover_duration (str, optional):
            Allowed layover duration range as "min,max" in minutes.
            Example: "90,330" (1.5 hours to 5.5 hours)

        exclude_conns (str, optional):
            Exclude connecting airports. Comma-separated IATA codes.
            Example: "ICN,NRT" (avoid connections through Seoul or Tokyo)

        sort_by (int, optional):
            Sort results by:
            - 1: Best overall (default)
            - 2: Price (lowest first)
            - 3: Departure time
            - 4: Arrival time
            - 5: Duration (shortest first)
            - 6: Emissions (lowest CO2 first)

        currency (str, optional):
            Currency code for prices. Default: "VND".
            Examples: "VND", "USD", "EUR", "JPY"

        gl (str, optional):
            Country code for localized results. Default: "vn".
            Examples: "vn", "us", "jp"

        hl (str, optional):
            Language code. Default: "vi".
            Examples: "vi", "en", "ja"

        show_hidden (bool, optional):
            Include hidden flights (long layovers, inconvenient times). Default: False.

        departure_token (str, optional):
            Token to retrieve return flights after selecting an outbound flight.
            Obtained from a previous search result.

        booking_token (str, optional):
            Token to retrieve booking options for a selected flight.
            Obtained from a previous search result.

    Output:
        list[dict]: A list of flights, each containing:

            price (int): Ticket price in the specified currency.
            total_duration (int): Total flight time in minutes.
            type (str): "One way" or "Round trip".
            booking_token (str): Token to retrieve booking links.
            departure_token (str): Token to retrieve return flights (round trip only).

            segments (list[dict]): Individual flight segments.
                departure_airport (str): Departure airport IATA code.
                departure_airport_name (str): Departure airport full name.
                departure_time (str): Departure time "YYYY-MM-DD HH:MM".
                arrival_airport (str): Arrival airport IATA code.
                arrival_airport_name (str): Arrival airport full name.
                arrival_time (str): Arrival time "YYYY-MM-DD HH:MM".
                duration (int): Segment duration in minutes.
                airline (str): Airline name.
                airline_logo (str): URL to airline logo image.
                flight_number (str): Flight number (e.g. "CX 766").
                airplane (str): Aircraft type (e.g. "Boeing 777").
                travel_class (str): Cabin class name (e.g. "Economy").
                legroom (str): Legroom measurement (e.g. "81 cm").
                amenities (list[str]): Amenities (Wi-Fi, USB, video, etc.).
                overnight (bool): True if overnight flight.
                often_delayed (bool): True if often delayed by over 30 minutes.

            layovers (list[dict]): Connections between segments.
                airport (str): Layover airport IATA code.
                airport_name (str): Layover airport full name.
                duration (int): Wait time in minutes.

            carbon_emissions (dict):
                this_flight (int): CO2 in grams for this flight.
                typical_for_this_route (int): Average CO2 for this route.
                difference_percent (int): % difference from average.

        Returns None if an error occurs.
    """


    raw = _search(
        departure_id=departure_id,
        arrival_id=arrival_id,
        outbound_date=outbound_date,
        return_date=return_date,
        adults=adults,
        children=children,
        infants_in_seat=infants_in_seat,
        infants_on_lap=infants_on_lap,
        travel_class=travel_class,
        stops=stops,
        max_price=max_price,
        max_duration=max_duration,
        bags=bags,
        outbound_times=outbound_times,
        return_times=return_times,
        layover_duration=layover_duration,
        exclude_conns=exclude_conns,
        sort_by=sort_by,
        currency=currency,
        gl=gl,
        hl=hl,
        show_hidden=show_hidden,
        departure_token=departure_token,
        booking_token=booking_token,
    )
    if raw is None:
        return {"error": "API request failed. No flight data available.", "flights": []}

    flights = _clean_response(raw)
    # Filter out flights with no price data
    flights = [f for f in flights if f.get("price", 0) > 0]
    if not flights:
        return {"error": "No flights found for this route/date.", "flights": []}

    return {"error": None, "flights": flights}

def _search_flights_web(last_search_result, **kwargs):
    """Wrapper: stores full results for frontend, returns summary to AI."""
    # Record tool call params
    call_info = {k: v for k, v in kwargs.items() if v is not None and v != 0 and v != ""}
    last_search_result["tool_calls"].append(call_info)

    result = search_flights(**kwargs)
    flights = result.get("flights", [])
    error = result.get("error")

    # Store full data for frontend
    last_search_result["flights"] = flights

    # If error or no flights, pass as-is so AI can retry
    if error or not flights:
        return {"error": error or "No flights found.", "found": 0}

    # Build summary for AI (save context)
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
        "currency": kwargs.get("currency", "VND"),
        "airlines": airlines,
        "duration_min": min(durations),
        "duration_max": max(durations),
        "note": "Full flight details are displayed to the user in the right panel. "
                "Summarize: how many flights found, price range, airlines. "
                "Ask if they want to filter or adjust."
    }
    return summary