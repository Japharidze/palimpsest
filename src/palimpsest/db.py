def add_to_watchlist(conn, tickers: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Add tickers to the watchlist.

    Returns (added, already_watching, not_found), all as tickers.
    """
    with conn.cursor() as cur:
        cur.execute(
            "select ticker, cik from company_tickers where ticker = any(%s)",
            (tickers,),
        )
        resolved = dict(cur.fetchall())          # ticker -> cik

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
        cur.execute("""
            create temp table temp_companies (
                cik text,
                ticker text,
                name text
            ) on commit drop
        """)

        with cur.copy("COPY temp_companies (cik, ticker, name) FROM STDIN") as copy:
            for r in rows:
                copy.write_row(r)

        cur.execute("""
            insert into companies (cik, name)
            select distinct on (cik) cik, name
            from temp_companies
            order by cik, ticker
            on conflict (cik) do update set name = excluded.name
        """)

        cur.execute("""
            insert into company_tickers (cik, ticker)
            select distinct cik, ticker from temp_companies
            on conflict (cik, ticker) do nothing
        """)

def upsert_filings(conn, rows) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TEMP TABLE temp_filings (
                accession_number text,
                cik text,
                form text,
                filing_date date,
                report_date date,
                primary_document text,
                document_key text
            ) ON COMMIT DROP;
        """)

        with cur.copy("""
            COPY temp_filings (
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
            FROM temp_filings
            ON CONFLICT (accession_number) DO NOTHING;
        """)
