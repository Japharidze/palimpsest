from datetime import date
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from palimpsest.chunks import search
from palimpsest.embedding import Embedder


class Toolbox:
    """Holds the connection and embedder so tool functions take only
    arguments the model should supply."""

    def __init__(self, conn, embedder: Embedder):
        self._conn = conn
        self._embedder = embedder

    # ------------------------------------------------------------------ #

    def _resolve_cik(self, ticker: str) -> str | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "select cik from company_tickers where ticker = %s",
                (ticker.upper(),),
            )
            row = cur.fetchone()
        return row[0] if row else None

    # ------------------------------------------------------------------ #

    def search_chunks(
        self,
        query: str,
        ticker: str | None = None,
        form: str | None = None,
        section: str | None = None,
        since: str | None = None,
    ) -> str:
        """Search the text of SEC filings for passages relevant to a query.

        Args:
            query: What to search for, in natural language.
            ticker: Optional stock ticker to restrict the search, e.g. "NVDA".
            form: Optional filing type, one of "10-K", "10-Q", "8-K", "20-F", "S-1".
            section: Optional section label, e.g. "risk_factors", "mda",
                "legal_proceedings", "controls", "cybersecurity".
            since: Optional ISO date; only filings on or after this date.
        """
        since_date = None
        if since:
            try:
                since_date = date.fromisoformat(since)
            except ValueError:
                return f"Invalid date {since!r}; expected YYYY-MM-DD."

        rows = search(
            self._conn,
            self._embedder,
            query,
            ticker=ticker,
            form=form,
            section=section,
            since=since_date,
        )
        if not rows:
            return "No matching passages found."

        return "\n\n".join(
            f"[{r['accession_number']} | {r['form']} | {r['section']} "
            f"| filed {r['filing_date']} | offset {r['start_offset']}]\n"
            f"{r['content']}"
            for r in rows
        )

    # ------------------------------------------------------------------ #

    def get_company_metrics(self, ticker: str, quarters: int = 4) -> str:
        """Get recent quarterly financial metrics and red flags for a company.

        Args:
            ticker: Stock ticker, e.g. "MSFT".
            quarters: How many recent quarters to return (default 4, max 12).
        """
        cik = self._resolve_cik(ticker)
        if cik is None:
            return f"No company found for ticker {ticker!r}."

        quarters = max(1, min(quarters, 12))

        with self._conn.cursor() as cur:
            cur.execute(
                """
                select period_end, revenue, gross_margin, net_income,
                       roa, roe, revenue_growth_yoy, inventory_growth_yoy,
                       flag_margin_compression, flag_inventory_buildup,
                       flag_receivables_buildup, flag_roa_deterioration
                from analytics.rpt_company_quarter
                where cik = %s
                order by period_end desc
                limit %s
                """,
                (cik, quarters),
            )
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]

        if not rows:
            return f"No quarterly metrics available for {ticker}."

        lines = []
        for row in rows:
            d: dict[str, Any] = dict(zip(cols, row))
            flags = [
                k.removeprefix("flag_")
                for k, v in d.items()
                if k.startswith("flag_") and v
            ]
            lines.append(
                f"{d['period_end']}: revenue={d['revenue']}, "
                f"gross_margin={d['gross_margin']}, net_income={d['net_income']}, "
                f"roa={d['roa']}, roe={d['roe']}, "
                f"revenue_growth_yoy={d['revenue_growth_yoy']}, "
                f"flags={', '.join(flags) or 'none'}"
            )
        return f"Quarterly metrics for {ticker}:\n" + "\n".join(lines)

    # ------------------------------------------------------------------ #

    def get_recent_changes(
        self,
        ticker: str,
        section: str | None = None,
        limit: int = 20,
    ) -> str:
        """Get paragraphs that changed between a company's two most recent filings.

        Args:
            ticker: Stock ticker, e.g. "NVDA".
            section: Optional section label to restrict to, e.g. "risk_factors".
            limit: Maximum number of changes to return (default 20).
        """
        cik = self._resolve_cik(ticker)
        if cik is None:
            return f"No company found for ticker {ticker!r}."

        with self._conn.cursor() as cur:
            cur.execute(
                """
                select label, change_type, to_filing_date, similarity,
                       summary, from_text, to_text
                from analytics.rpt_section_changes
                where cik = %s
                  and (%s::text is null or label = %s)
                order by to_filing_date desc, label, position
                limit %s
                """,
                (cik, section, section, limit),
            )
            rows = cur.fetchall()

        if not rows:
            return f"No recorded changes for {ticker}."

        lines = []
        for label, ctype, filed, sim, summary, from_text, to_text in rows:
            text = to_text or from_text or ""
            lines.append(
                f"[{filed} | {label} | {ctype}"
                + (f" | similarity {sim:.2f}" if sim is not None else "")
                + "]\n"
                + (f"Summary: {summary}\n" if summary else "")
                + f"Text: {text[:600]}"
            )
        return f"Recent changes for {ticker}:\n\n" + "\n\n".join(lines)


# Define explicit schemas matching your functions exactly
class SearchChunksInput(BaseModel):
    query: str = Field(description="What to search for, in natural language.")
    ticker: str | None = Field(
        default=None,
        description="Optional stock ticker to restrict the search, e.g. 'NVDA'.",
    )
    form: str | None = Field(
        default=None,
        description="Optional filing type, one of '10-K', '10-Q', '8-K', '20-F', 'S-1'.",
    )
    section: str | None = Field(
        default=None, description="Optional section label, e.g. 'risk_factors', 'mda'."
    )
    since: str | None = Field(
        default=None,
        description="Optional ISO date; only filings on or after this date.",
    )


class GetCompanyMetricsInput(BaseModel):
    ticker: str = Field(description="Stock ticker, e.g. 'MSFT'.")
    quarters: int = Field(
        default=4, description="How many recent quarters to return (default 4, max 12)."
    )


class GetRecentChangesInput(BaseModel):
    ticker: str = Field(description="Stock ticker, e.g. 'NVDA'.")
    section: str | None = Field(
        default=None,
        description="Optional section label to restrict to, e.g. 'risk_factors'.",
    )
    limit: int = Field(
        default=20, description="Maximum number of changes to return (default 20)."
    )


def build_registry(toolbox: Toolbox) -> dict[str, Any]:
    """Explicit name -> callable map. Only these can be invoked."""
    return {
        "search_chunks": StructuredTool.from_function(
            func=toolbox.search_chunks,
            name="search_chunks",
            args_schema=SearchChunksInput,
        ),
        "get_company_metrics": StructuredTool.from_function(
            func=toolbox.get_company_metrics,
            name="get_company_metrics",
            args_schema=GetCompanyMetricsInput,
        ),
        "get_recent_changes": StructuredTool.from_function(
            func=toolbox.get_recent_changes,
            name="get_recent_changes",
            args_schema=GetRecentChangesInput,
        ),
    }
