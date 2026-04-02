
from typing import Optional
from pydantic import BaseModel, Field

class SearchFlightsInput(BaseModel):
    departure_id: str = Field(description="Departure airport IATA code(s), comma-separated.")
    arrival_id: str = Field(description="Arrival airport IATA code(s), comma-separated.")
    outbound_date: str = Field(description="Departure date YYYY-MM-DD.")
    return_date: Optional[str] = Field(default=None, description="Return date for round trip.")
    adults: int = Field(default=1, description="Adult passengers.")
    children: int = Field(default=0, description="Child passengers.")
    infants_in_seat: int = Field(default=0, description="Infants with own seat.")
    infants_on_lap: int = Field(default=0, description="Infants on lap.")
    travel_class: int = Field(default=1, description="1=Economy, 2=Premium Economy, 3=Business, 4=First.")
    stops: int = Field(default=0, description="0=Any, 1=Nonstop, 2=Max 1 stop, 3=Max 2 stops.")
    max_price: Optional[int] = Field(default=None, description="Max price.")
    max_duration: Optional[int] = Field(default=None, description="Max duration in minutes.")
    bags: int = Field(default=0, description="Checked bags.")
    outbound_times: Optional[str] = Field(default=None, description="Departure time range e.g. '6,18'.")
    return_times: Optional[str] = Field(default=None, description="Return time range.")
    layover_duration: Optional[str] = Field(default=None, description="Layover range 'min,max' in minutes.")
    exclude_conns: Optional[str] = Field(default=None, description="Exclude connecting airports.")
    sort_by: int = Field(default=1, description="1=Best, 2=Price, 3=Departure, 4=Arrival, 5=Duration.")
    currency: str = Field(default="VND", description="Currency code.")
    gl: str = Field(default="vn", description="Country code.")
    hl: str = Field(default="vi", description="Language code.")
    show_hidden: bool = Field(default=False, description="Include hidden flights.")
    departure_token: Optional[str] = Field(default=None, description="Token for return flights.")
    booking_token: Optional[str] = Field(default=None, description="Token for booking options.")

class SearchAgentInput(BaseModel):
    query: str = Field(
        description="A plain, natural language string containing all the flight requirements (e.g., origin, destination, dates, cabin class, max price). Example: 'Please search for flights from Hanoi to Ho Chi Minh City on 2023-11-20 for 2 adults in Business class under 5 million VND.'"
    )

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class ChatResponse(BaseModel):
    response: str
    flights: list[dict] = []
    tool_calls: list[dict] = []
    searched: bool = False
