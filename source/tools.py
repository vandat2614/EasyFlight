import os
import json
import requests
from typing import Optional
from source.utils import _generate_cache_key

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
    include_airlines: Optional[str] = None,
    exclude_airlines: Optional[str] = None,
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

        include_airlines (str, optional):
            Only show flights from these airlines (comma-separated IATA). Cannot be used with exclude_airlines.
        
        exclude_airlines (str, optional): 
            Exclude flights from these airlines (comma-separated IATA). Cannot be used with include_airlines.

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


    _BASE_URL = "https://serpapi.com/search"
    SERP_API_KEY = os.environ["SERP_API_KEY"]

    # --- 1. Build required params ---
    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "type": 2 if return_date is None else 1,
        "adults": adults,
        "travel_class": travel_class,
        "stops": stops,
        "sort_by": sort_by,
        "currency": currency,
        "gl": gl,
        "hl": hl,
        "api_key": SERP_API_KEY,
    }

    # --- 2. Add optional params (only when set) ---
    optional = {
        "return_date": return_date,
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
        "departure_token": departure_token,
        "booking_token": booking_token,
    }

    for k, v in optional.items():
        if v is not None:
            params[k] = v

    # Boolean flags (only send when True)
    if show_hidden:
        params["show_hidden"] = "true"

    # --- 3. Call API ---
    print(f"[SEARCH] {departure_id}->{arrival_id} {outbound_date}")
    try:
        response = requests.get(_BASE_URL, params=params)
        response.raise_for_status()
        raw_data = response.json()
    except Exception as e:
        raise e

    return raw_data

def search_flights_wrapper(**kwargs):

    try:
        response = search_flights(**kwargs)
    except Exception as e:

        error = str(e)
        if 'http' in error:
            try:
                url = ':'.join(error.split(':')[-2:])
                error = requests.get(url).json()['error']
            except:
                pass

        return json.dumps({
            "status": "error", 
            "message": error
        })
    
    
    # flights = _clean_response(response)
    # if not flights:
    #     return json.dumps({
    #         "status": "error", 
    #         "message": "No flights found"
    #     })    

    cache_key = _generate_cache_key(kwargs)
    cache_path = os.path.join('cache', f'{cache_key}.json')
    if not os.path.exists('cache'):
        os.makedirs('cache', exist_ok=True)

    with open(file=cache_path, mode='w', encoding='utf-8') as file:
        json.dump(response, file, ensure_ascii=False, indent=4)
    print(f'[CACHE] {cache_path}')

    return json.dumps({
        "status": "success",
        "cache_key": cache_key
    })

