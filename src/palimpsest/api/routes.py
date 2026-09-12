import json
import time
from datetime import date
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from langchain_core.runnables import RunnableConfig

from palimpsest.api.schemas import (
    AskRequest,
    AskResponse,
    Company,
    CorpusStats,
    Fact,
    FeedChange,
    FilingSection,
    Meta,
    QuarterlyRow,
    RecentChange,
)
from palimpsest.config import EVAL_RESULTS, settings
from palimpsest.db import (
    fetch_company_recent_changes,
    fetch_corpus_stats,
    fetch_facts,
    fetch_feed_changes,
    fetch_filing_section,
    fetch_quarterly_rows,
    fetch_watchlist,
    resolve_cik,
)

router = APIRouter()


@router.post("/ask")
def ask(request: Request, ask: AskRequest):
    messages = [{"role": "user", "content": ask.question}]
    conversation_id = ask.conversation_id or str(uuid4())
    config: RunnableConfig = {"configurable": {"thread_id": conversation_id}}

    start = time.monotonic()
    result = request.app.state.agent.invoke(
        {"messages": messages, "iterations": 0}, config=config
    )
    latency_ms = int((time.monotonic() - start) * 1000)

    last_message = result["messages"][-1]

    return AskResponse(
        answer=last_message["content"],
        citation_problems=result.get("citation_problems"),
        tool_calls=[c for m in result["messages"] for c in (m.get("tool_calls") or [])],
        latency_ms=latency_ms,
        conversation_id=conversation_id,
    )


@router.get("/companies")
def watchlist(request: Request) -> list[Company]:
    companies = []
    for row in fetch_watchlist(request.app.state.pool):
        companies.append(
            Company(
                ticker=row["ticker"],
                name=row["name"],
                period_end=row["period_end"],
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
) -> list[QuarterlyRow]:

    pool = request.app.state.pool
    cik = resolve_cik(pool, ticker)
    if cik is None:
        raise HTTPException(404, f"Unknown ticker {ticker}")
    rows = fetch_quarterly_rows(
        pool=request.app.state.pool, cik=cik, since=since, until=until
    )
    quarterly_rows = [
        QuarterlyRow(
            period_end=r["period_end"],
            source_accn=r["source_accn"],
            revenue=r["revenue"],
            net_income=r["net_income"],
            gross_margin_pct=r["gross_margin_pct"],
            roa_pct=r["roa_pct"],
            roe_pct=r["roe_pct"],
            revenue_growth_yoy_pct=r["revenue_growth_yoy_pct"],
            inventory_growth_yoy_pct=r["inventory_growth_yoy_pct"],
            receivables_growth_yoy_pct=r["receivables_growth_yoy_pct"],
            runway_quarters=r["runway_quarters"],
            revenue_is_derived=r["revenue_is_derived"],
            flag_margin_compression=r["flag_margin_compression"],
            flag_inventory_buildup=r["flag_inventory_buildup"],
            flag_receivables_buildup=r["flag_receivables_buildup"],
            flag_roa_deterioration=r["flag_roa_deterioration"],
            flag_short_runway=r["flag_short_runway"],
        )
        for r in rows
    ]
    return quarterly_rows


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


@router.get("/companies/changes")
def feed_changes(request: Request, limit: int = 20) -> list[FeedChange]:
    rows = fetch_feed_changes(request.app.state.pool, limit)
    feed = [
        FeedChange(
            ticker=c["ticker"],
            company_name=c["company_name"],
            cik=c["cik"],
            label=c["label"],
            change_type=c["change_type"],
            to_filing_date=c["to_filing_date"],
            to_accession=c["to_accession"],
            from_accession=c["from_accession"],
            similarity=c["similarity"],
            summary=c["summary"],
            importance=c["importance"],
        )
        for c in rows
    ]

    return feed


@router.get("/filings/{accession}")
def filing_section(
    request: Request,
    accession: str,
    section: str | None = None,
    section_label: str | None = None,
) -> FilingSection:

    if not section and not section_label:
        raise HTTPException(404, "Either section or section label should be provided")

    filing_section = fetch_filing_section(
        pool=request.app.state.pool,
        accession_number=accession,
        section=section,
        section_label=section_label,
    )

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


@router.get("/filings/{accession}/facts")
def fact(request: Request, accession: str) -> list[Fact]:
    rows = fetch_facts(request.app.state.pool, accession)

    facts = [
        Fact(
            tag=r["tag"],
            unit=r["unit"],
            start_date=r["start_date"],
            end_date=r["end_date"],
            duration=r["duration"],
            value=r["val"],
            filed=r["filed"],
            metric=r["metric"],
        )
        for r in rows
    ]

    return facts


@router.get("/evals")
def evals():
    evals_path = max(EVAL_RESULTS.glob("*.json"), default=None)
    if not evals_path:
        raise HTTPException(404, "Evaluation does not exist")
    with open(evals_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


@router.get("/meta")
def meta(request: Request) -> Meta:
    stats = fetch_corpus_stats(request.app.state.pool)
    return Meta(
        agent_model=settings.agent_model,
        agent_provider=settings.agent_provider,
        summarizer_model=settings.summarizer_model,
        embedding_model=settings.embedding_model,
        corpus=CorpusStats(**stats),
    )
