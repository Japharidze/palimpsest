from datetime import date

from pydantic import BaseModel


class Company(BaseModel):
    ticker: str
    name: str
    latest_filing_date: date
    margin_compression: bool
    inventory_buildup: bool
    receivables_buildup: bool
    roa_deterioration: bool
    short_runway: bool


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    citation_problems: list[str]
    tool_calls: list[dict]
    latency_ms: int


class WatchlistResponse(BaseModel):
    companies: list[Company]
