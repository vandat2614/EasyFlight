import json
import hashlib

def _generate_cache_key(params: dict) -> str:
    """
    Generate a consistent and concise Hash Key from a parameter dictionary.
    """
    clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
    param_str = json.dumps(clean_params, sort_keys=True)
    
    hash_code = hashlib.md5(param_str.encode('utf-8')).hexdigest()
    return hash_code

# --- Clean function ---

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