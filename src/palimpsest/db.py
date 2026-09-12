from datetime import date
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _temp_table_query(table: str) -> str:
    return f"""
        create temp table tmp_{table} on commit drop as
        select * from {table} limit 0
    """


def add_to_watchlist(
    conn, tickers: list[str]
) -> tuple[list[str], list[str], list[str]]:
    """Add tickers to the watchlist.

    Returns (added, already_watching, not_found), all as tickers.
    """
    with conn.cursor() as cur:
        cur.execute(
            "select ticker, cik from company_tickers where ticker = any(%s)",
            (tickers,),
        )
        resolved = dict(cur.fetchall())  # ticker -> cik

        not_found = [t for t in tickers if t not in resolved]
        if not resolved:
            return [], [], not_found

        cur.execute(
            """
            insert into watchlist (cik)
            select unnest(%s::text[])
            on conflict (cik) do nothing
            returning cik
            """,
            (list(resolved.values()),),
        )
        inserted_ciks = {row[0] for row in cur.fetchall()}

    added = [t for t, c in resolved.items() if c in inserted_ciks]
    already = [t for t, c in resolved.items() if c not in inserted_ciks]
    return added, already, not_found


def upsert_companies(conn, rows) -> None:
    with conn.cursor() as cur:
        cur.execute(_temp_table_query("companies"))

        with cur.copy("COPY tmp_companies (cik, name) FROM STDIN") as copy:
            for r in rows:
                copy.write_row(r)

        cur.execute("""
            insert into companies (cik, name)
            select distinct on (cik) cik, name
            from tmp_companies
            order by cik, name
            on conflict (cik) do update set name = excluded.name
        """)


def upsert_company_tickers(conn, rows) -> None:
    with conn.cursor().copy("COPY company_tickers (cik, ticker) FROM STDIN") as copy:
        for r in rows:
            copy.write_row(r)


def upsert_filings(conn, rows) -> None:
    with conn.cursor() as cur:
        cur.execute(_temp_table_query("filings"))

        with cur.copy("""
            COPY tmp_filings (
                accession_number,
                cik,
                form,
                filing_date,
                report_date,
                primary_document,
                document_key
            ) FROM STDIN
        """) as copy:
            for r in rows:
                copy.write_row(r)

        cur.execute("""
            INSERT INTO filings (
                accession_number,
                cik,
                form,
                filing_date,
                report_date,
                primary_document,
                document_key
            )
            SELECT 
                accession_number,
                cik,
                form,
                filing_date,
                report_date,
                primary_document,
                document_key
            FROM tmp_filings
            ON CONFLICT (accession_number) DO NOTHING;
        """)


def upsert_facts(conn, rows) -> int:
    with conn.cursor() as cur:
        cur.execute(_temp_table_query("xbrl_facts"))

        with cur.copy("""
            COPY tmp_xbrl_facts (
                cik,
                taxonomy,
                tag,
                unit,
                start_date,
                end_date,
                val,
                accn,
                form,
                filed
            ) FROM STDIN
        """) as copy:
            for r in rows:
                copy.write_row(r)

        cur.execute("""
            INSERT INTO xbrl_facts (
                cik,
                taxonomy,
                tag,
                unit,
                start_date,
                end_date,
                val,
                accn,
                form,
                filed
            )
            SELECT 
                cik,
                taxonomy,
                tag,
                unit,
                start_date,
                end_date,
                val,
                accn,
                form,
                filed
            FROM tmp_xbrl_facts
            ON CONFLICT (cik, taxonomy, tag, unit, accn, end_date, start_date) DO NOTHING;
        """)
        inserted = cur.rowcount

    return inserted


def upsert_sections(conn, rows) -> int:
    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.execute(_temp_table_query("filing_sections"))

        with cur.copy("""COPY tmp_filing_sections (
                        accession_number,
                        section,
                        content,
                        start_offset,
                        end_offset,
                        confidence,
                        detection_method) FROM STDIN
                      """) as copy:
            for r in rows:
                copy.write_row(r)

        cur.execute("""
            insert into filing_sections (accession_number, section, content, start_offset, end_offset, confidence,
            detection_method)
            select accession_number, section, content, start_offset, end_offset, confidence, detection_method from tmp_filing_sections
            on conflict (accession_number, section) do update set 
                content          = excluded.content,
                start_offset     = excluded.start_offset,
                end_offset       = excluded.end_offset,
                confidence       = excluded.confidence,
                detection_method = excluded.detection_method
        """)
        inserted = cur.rowcount

        return inserted


def upsert_section_changes(conn, rows) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.execute(
            """
            delete from section_changes
            where from_accession = %s and to_accession = %s and label = %s
        """,
            (rows[0][3], rows[0][4], rows[0][2]),
        )

        with cur.copy("""
            COPY section_changes (
                cik, form, label, from_accession, to_accession,
                change_type, from_text, to_text, similarity, position
            ) FROM STDIN
        """) as copy:
            for r in rows:
                copy.write_row(r)

        inserted = cur.rowcount
    return inserted


def upsert_change_summaries(conn, row: tuple) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO change_summaries
                (text_hash, summary, model, created_at)
            VALUES
                (%s, %s, %s, %s);
        """,
            row,
        )


def upsert_chunk(conn, row: tuple) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO section_chunks
                (accession_number, section, chunk_index, start_offset, end_offset, content, embedding)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """,
            row,
        )

        has_inserted = bool(cur.rowcount)
    return has_inserted


def resolve_cik(pool, ticker: str) -> str | None:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select cik from company_tickers where ticker = %s",
            (ticker.upper(),),
        )
        row = cur.fetchone()
    return row[0] if row else None


def fetch_company_report_range(pool: ConnectionPool, cik: str) -> tuple[Any, Any]:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                select min(period_end), max(period_end)
                from analytics.rpt_company_quarter
                where cik = %s
                """,
            (cik,),
        )
        earliest, latest = cur.fetchone() or []
    return earliest, latest


def fetch_company_metrics(
    pool: ConnectionPool, cik: str, since: date | None, until: date | None, limit: int
) -> list[dict]:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
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
                "since": since,
                "until": until,
                "limit": limit,
            },
        )
        rows = cur.fetchall()

    return rows


def fetch_company_recent_changes(
    pool: ConnectionPool, cik: str, section: str | None, limit: int
) -> list[dict]:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
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

    return rows


def fetch_feed_changes(pool: ConnectionPool, limit: int) -> list[dict]:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select ticker, company_name, cik, label, change_type,
                to_filing_date, to_accession, from_accession, similarity, summary,
                round((
                    case
                        when change_type in ('added', 'removed') then 1.0
                        else 1.0 - coalesce(similarity, 1.0)
                    end
                    * case label
                        when 'risk_factors' then 1.0
                        when 'legal_proceedings' then 0.9
                        when 'cybersecurity' then 0.8
                        when 'mda' then 0.6
                        when 'controls' then 0.4
                        else 0.3
                        end
                )::numeric, 3) as importance
            from analytics.rpt_section_changes
            where summary is not null
            order by importance desc, to_filing_date desc
            limit %s
                """,
            (limit,),
        )
        rows = cur.fetchall()

    return rows


def fetch_watchlist(pool: ConnectionPool) -> list[dict]:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            select
                t.ticker,
                c.name,
                q.period_end,
                q.source_accn,
                q.flag_margin_compression,
                q.flag_inventory_buildup,
                q.flag_receivables_buildup,
                q.flag_roa_deterioration,
                q.flag_short_runway
            from watchlist w
            join companies c using (cik)
            join company_tickers ct using (cik)
            join lateral (
                select * from analytics.rpt_company_quarter r
                where r.cik = w.cik
                order by r.period_end desc
                limit 1
            ) q on true
            join lateral (
                select ticker from company_tickers
                where cik = w.cik
                order by length(ticker), ticker
                limit 1
            ) t on true
            group by t.ticker, c.name, q.period_end, q.source_accn,
                    q.flag_margin_compression, q.flag_inventory_buildup,
                    q.flag_receivables_buildup, q.flag_roa_deterioration,
                    q.flag_short_runway
            order by c.name
        """)
        rows = cur.fetchall()

    return rows


def fetch_quarterly_rows(
    pool: ConnectionPool, cik: str, since: date | None, until: date | None
) -> list[dict]:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
                period_end,
                source_accn,
                revenue,
                net_income,
                gross_margin_pct,
                roa_pct,
                roe_pct,
                revenue_growth_yoy_pct,
                inventory_growth_yoy_pct,
                receivables_growth_yoy_pct,
                runway_quarters,
                revenue_is_derived,
                flag_margin_compression,
                flag_inventory_buildup,
                flag_receivables_buildup,
                flag_roa_deterioration,
                flag_short_runway
            from analytics.rpt_company_quarter
            where cik = %s
              and (%s::date is null or period_end >= %s)
              and (%s::date is null or period_end <= %s)
            order by period_end desc
            """,
            (cik, since, since, until, until),
        )
        rows = cur.fetchall()

    return rows


def fetch_filing_section(pool, accession_number, section, section_label) -> dict | None:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
        select
            s.accession_number,
            s.section,
            sl.label,
            s.content,
            s.start_offset,
            s.end_offset,
            s.confidence
        from filing_sections s
        join filings f using (accession_number)
        left join analytics.section_labels sl
            on sl.form = replace(f.form, '/A', '')
           and sl.section_key = s.section
        where s.accession_number = %s
          and (s.section = %s or sl.label = %s)
        """,
            (accession_number, section, section_label),
        )
        filing_section = cur.fetchone()

    return filing_section


def fetch_facts(pool, accession_number) -> list[dict]:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select f.tag, f.unit, f.start_date, f.end_date, f.duration,
                f.val, f.filed, m.metric
            from xbrl_facts f
            left join analytics.metric_tags m using (tag)
            where f.accn = %s
            and f.taxonomy = 'us-gaap'
            and m.metric is not null
            order by m.metric, f.end_date desc
        """,
            (accession_number,),
        )
        facts = cur.fetchall()

    return facts


def fetch_corpus_stats(pool: ConnectionPool) -> dict:
    """Counts describing what is currently ingested."""
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            select
                (select count(*) from watchlist)                    as companies,
                (select count(*) from filings f
                   join watchlist w using (cik))                    as filings,
                (select count(*) from filing_sections)              as sections,
                (select count(*) from xbrl_facts)                   as facts,
                (select count(*) from section_changes)              as changes,
                (select count(*) from change_summaries)             as summaries,
                (select count(*) from section_chunks)               as chunks,
                (select max(filing_date) from filings f
                   join watchlist w using (cik))                    as latest_filing
        """)
        return cur.fetchone() or {}
