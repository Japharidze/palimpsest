from datetime import date
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from palimpsest.chunks import search
from palimpsest.embedding import Embedder


class Toolbox:
    """Holds the connection and embedder so tool functions take only
    arguments the model should supply."""

    def __init__(self, pool, embedder: Embedder):
        self._pool = pool
        self._embedder = embedder

    # ------------------------------------------------------------------ #

    def _resolve_cik(self, ticker: str) -> str | None:
        with self._pool.connection() as conn, conn.cursor() as cur:
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
            self._pool,
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

    def get_company_metrics(
        self,
        ticker: str,
        since: str | None = None,
        until: str | None = None,
        quarters: int = 4,
    ) -> str:
        """Get quarterly financial metrics and red flags for a company.

        Returns the most recent quarters unless a date range is given. To ask
        about an older period, pass since and until.

        Args:
            ticker: Stock ticker, e.g. "MSFT".
            since: ISO date; only quarters ending on or after it.
            until: ISO date; only quarters ending on or before it.
            quarters: Maximum number of quarters to return (default 4, max 12).
        """
        cik = self._resolve_cik(ticker)
        if cik is None:
            return f"No company found for ticker {ticker!r}."

        bounds: dict[str, date | None] = {"since": None, "until": None}
        for name, raw in (("since", since), ("until", until)):
            if raw:
                try:
                    bounds[name] = date.fromisoformat(raw)
                except ValueError:
                    return f"Invalid {name} date {raw!r}; expected YYYY-MM-DD."

        quarters = max(1, min(quarters, 12))

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    select source_accn, period_end, revenue, net_income,
                        gross_margin_pct, roa_pct, roe_pct,
                        revenue_growth_yoy_pct, inventory_growth_yoy_pct,
                        receivables_growth_yoy_pct, runway_quarters,
                        flag_margin_compression, flag_inventory_buildup,
                        flag_receivables_buildup, flag_roa_deterioration,
                        flag_short_runway
                    from analytics.rpt_company_quarter
                    where cik = %(cik)s
                    and (%(since)s::date is null or period_end >= %(since)s)
                    and (%(until)s::date is null or period_end <= %(until)s)
                    order by period_end desc
                    limit %(limit)s
                    """,
                {
                    "cik": cik,
                    "since": bounds["since"],
                    "until": bounds["until"],
                    "limit": quarters,
                },
            )
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]

        if not rows:
            with self._pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        select min(period_end), max(period_end)
                        from analytics.rpt_company_quarter
                        where cik = %s
                        """,
                    (cik,),
                )
                earliest, latest = cur.fetchone()
            if earliest is None:
                return f"No quarterly metrics available for {ticker}."
            return (
                f"No quarters found for {ticker} in that range. "
                f"Available quarters run from {earliest} to {latest}."
            )

        lines = []
        for row in rows:
            d: dict[str, Any] = dict(zip(cols, row))
            flags = [
                k.removeprefix("flag_")
                for k, v in d.items()
                if k.startswith("flag_") and v
            ]
            parts = [
                f"revenue={d['revenue']}",
                f"net_income={d['net_income']}",
                f"gross_margin={d['gross_margin_pct']}%",
                f"roa={d['roa_pct']}%",
                f"roe={d['roe_pct']}%",
                f"revenue_growth_yoy={d['revenue_growth_yoy_pct']}%",
                f"inventory_growth_yoy={d['inventory_growth_yoy_pct']}%",
                f"receivables_growth_yoy={d['receivables_growth_yoy_pct']}%",
            ]
            if d["runway_quarters"] is not None:
                parts.append(f"runway_quarters={d['runway_quarters']}")
            parts.append(f"flags={', '.join(flags) or 'none'}")

            lines.append(f"{d['period_end']} [{d['source_accn']}]: " + ", ".join(parts))

        return f"Quarterly metrics for {ticker}:\n" + "\n".join(lines)

    # ------------------------------------------------------------------ #

    def get_recent_changes(
        self,
        ticker: str,
        section: str | None = None,
        limit: int = 20,
    ) -> str:
        """Get paragraphs that changed between a company's two most recent filings.

        Each change names two filings: the earlier one it came from and the
        later one it went to. Removed text exists only in the earlier filing;
        added text only in the later one.

        Args:
            ticker: Stock ticker, e.g. "NVDA".
            section: Optional section label to restrict to, e.g. "risk_factors".
            limit: Maximum number of changes to return (default 20).
        """
        cik = self._resolve_cik(ticker)
        if cik is None:
            return f"No company found for ticker {ticker!r}."

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                    select label, change_type, from_accession, to_accession,
                        from_filing_date, to_filing_date, similarity,
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
        for (
            label,
            ctype,
            from_accn,
            to_accn,
            from_filed,
            to_filed,
            sim,
            summary,
            from_text,
            to_text,
        ) in rows:
            if ctype == "removed":
                source = f"cite {from_accn} (filed {from_filed})"
                text = from_text or ""
            elif ctype == "added":
                source = f"cite {to_accn} (filed {to_filed})"
                text = to_text or ""
            else:
                source = (
                    f"cite {from_accn} for the earlier wording, "
                    f"{to_accn} for the current wording"
                )
                text = to_text or from_text or ""

            header = f"[{label} | {ctype}"
            if sim is not None:
                header += f" | similarity {sim:.2f}"
            header += f" | {source}]"

            body = ""
            if summary:
                body += f"Summary: {summary}\n"
            if ctype == "modified" and from_text:
                body += f"Was: {from_text[:400]}\nNow: {text[:400]}"
            else:
                body += f"Text: {text[:600]}"

            lines.append(header + "\n" + body)

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
    since: str | None = Field(
        default=None,
        description="ISO date. Required when asking about any period other than the most recent quarters.",
    )
    until: str | None = Field(
        default=None, description="ISO date, upper bound on period end."
    )
    quarters: int = Field(default=4, description="Maximum quarters to return (max 12).")


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
