from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field

AccessionNumber = Annotated[str, Field(pattern=r"^\d{10}-\d{2}-\d{6}$")]


class Company(BaseModel):
    ticker: str
    name: str
    latest_filing_date: date
    margin_compression: bool
    inventory_buildup: bool
    receivables_buildup: bool
    roa_deterioration: bool
    short_runway: bool


class RecentChange(BaseModel):
    label: str
    change_type: str
    from_accession: AccessionNumber
    to_accession: AccessionNumber
    from_filing_date: date
    to_filing_date: date
    similarity: float | None = Field(ge=0.0, le=1.0)
    summary: str
    from_text: str | None
    to_text: str | None


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


class QuarterlyRowsResponse(BaseModel):
    rows: list[dict]


class FilingSection(BaseModel):
    accession: AccessionNumber
    section: str
    section_label: str | None
    content: str
    start_offset: int
    end_offset: int
    confidence: float = Field(ge=0.0, le=1.0)
