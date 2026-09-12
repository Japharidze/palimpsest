from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

AccessionNumber = Annotated[str, Field(pattern=r"^\d{10}-\d{2}-\d{6}$")]


class Company(BaseModel):
    ticker: str
    name: str
    period_end: date
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
    summary: str | None
    from_text: str | None
    to_text: str | None


class FeedChange(BaseModel):
    ticker: str
    company_name: str
    cik: str
    label: str
    change_type: str
    to_filing_date: date
    to_accession: AccessionNumber
    from_accession: AccessionNumber
    similarity: float | None
    summary: str
    importance: float


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    citation_problems: list[str]
    tool_calls: list[dict]
    latency_ms: int
    conversation_id: str


class QuarterlyRow(BaseModel):
    period_end: date
    source_accn: AccessionNumber | None
    revenue: Decimal | None
    net_income: Decimal | None
    gross_margin_pct: Decimal | None
    roa_pct: Decimal | None
    roe_pct: Decimal | None
    revenue_growth_yoy_pct: Decimal | None
    inventory_growth_yoy_pct: Decimal | None
    receivables_growth_yoy_pct: Decimal | None
    runway_quarters: Decimal | None
    revenue_is_derived: bool | None
    flag_margin_compression: bool
    flag_inventory_buildup: bool
    flag_receivables_buildup: bool
    flag_roa_deterioration: bool
    flag_short_runway: bool


class FilingSection(BaseModel):
    accession: AccessionNumber
    section: str
    section_label: str | None
    content: str
    start_offset: int
    end_offset: int
    confidence: float = Field(ge=0.0, le=1.0)


class Fact(BaseModel):
    tag: str
    unit: str
    start_date: date | None
    end_date: date
    duration: int | None
    value: Decimal
    filed: date
    metric: str


class CorpusStats(BaseModel):
    companies: int
    filings: int
    sections: int
    facts: int
    changes: int
    summaries: int
    chunks: int
    latest_filing: date | None


class Meta(BaseModel):
    agent_model: str
    agent_provider: str
    summarizer_model: str
    embedding_model: str
    corpus: CorpusStats
