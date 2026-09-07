import time

from fastapi import APIRouter, Request

from palimpsest.api.schemas import AskRequest, AskResponse, Company, WatchlistResponse
from palimpsest.db import fetch_watchlist

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
def watchlist(request: Request):
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

    return WatchlistResponse(companies=companies)
