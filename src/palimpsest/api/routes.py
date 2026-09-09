import json
import time
from datetime import date

from fastapi import APIRouter, HTTPException, Request

from palimpsest.api.schemas import (
    AskRequest,
    AskResponse,
    Company,
    FilingSection,
    QuarterlyRowsResponse,
    RecentChange,
)
from palimpsest.config import EVAL_RESULTS
from palimpsest.db import (
    fetch_company_recent_changes,
    fetch_filing_section,
    fetch_quarterly_rows,
    fetch_watchlist,
    resolve_cik,
)

router = APIRouter()


@router.post("/ask")
def ask(request: Request, ask: AskRequest):
    messages = [{"role": "user", "content": ask.question}]

    start = time.monotonic()
    result = request.app.state.agent.invoke({"messages": messages, "iterations": 0})
    latency_ms = int((time.monotonic() - start) * 1000)

    last_message = result["messages"][-1]

    return AskResponse(
        answer=last_message["content"],
        citation_problems=result.get("citation_problems"),
        tool_calls=[c for m in result["messages"] for c in (m.get("tool_calls") or [])],
        latency_ms=latency_ms,
    )


@router.get("/companies")
def watchlist(request: Request) -> list[Company]:
    companies = []
    for row in fetch_watchlist(request.app.state.pool):
        companies.append(
            Company(
                ticker=row["ticker"],
                name=row["name"],
                latest_filing_date=row["latest_filing_date"],
                margin_compression=row["flag_margin_compression"],
                inventory_buildup=row["flag_inventory_buildup"],
                receivables_buildup=row["flag_receivables_buildup"],
                roa_deterioration=row["flag_roa_deterioration"],
                short_runway=row["flag_short_runway"],
            )
        )

    return companies


@router.get("/companies/{ticker}/metrics")
def quarterly_rows(
    request: Request, ticker: str, since: date | None = None, until: date | None = None
):

    pool = request.app.state.pool
    cik = resolve_cik(pool, ticker)
    if cik is None:
        raise HTTPException(404, f"Unknown ticker {ticker}")
    rows = fetch_quarterly_rows(
        pool=request.app.state.pool, cik=cik, since=since, until=until
    )
    return QuarterlyRowsResponse(rows=rows)


@router.get("/companies/{ticker}/changes")
def recent_changes(
    request: Request, ticker: str, section: str | None = None, limit: int = 20
) -> list[RecentChange]:
    pool = request.app.state.pool
    cik = resolve_cik(pool, ticker)
    if cik is None:
        raise HTTPException(404, f"Unknown ticker {ticker}")
    rows = fetch_company_recent_changes(
        pool=pool, cik=cik, section=section, limit=limit
    )
    changes = [
        RecentChange(
            label=c["label"],
            change_type=c["change_type"],
            from_accession=c["from_accession"],
            to_accession=c["to_accession"],
            from_filing_date=c["from_filing_date"],
            to_filing_date=c["to_filing_date"],
            similarity=c["similarity"],
            summary=c["summary"],
            from_text=c["from_text"],
            to_text=c["to_text"],
        )
        for c in rows
    ]

    return changes


@router.get("/filings/{accession}")
def filing_section(
    request: Request,
    accession: str,
    section: str | None = None,
    section_label: str | None = None,
) -> FilingSection:

    filing_section = fetch_filing_section(
        pool=request.app.state.pool,
        accession_number=accession,
        section=section,
        section_label=section_label,
    )
    if not section and not section_label:
        raise HTTPException(404, "Either section or section label should be provided")

    provided = "section"
    if section_label:
        provided = "section_label"
        section = section_label

    if not filing_section:
        raise HTTPException(
            404,
            f"Unknown accession number - {accession} or wrong {provided} - {section}",
        )

    return FilingSection(
        accession=filing_section["accession_number"],
        section=filing_section["section"],
        section_label=filing_section["label"],
        content=filing_section["content"],
        start_offset=filing_section["start_offset"],
        end_offset=filing_section["end_offset"],
        confidence=filing_section["confidence"],
    )


@router.get("/evals")
def evals():
    evals_path = max(EVAL_RESULTS.glob("*.json"), default=None)
    if not evals_path:
        raise HTTPException(404, "Evaluation does not exist")
    with open(evals_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data
