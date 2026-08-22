def upsert_companies(conn, rows) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TEMP TABLE temp_companies (
                cik text,
                ticker text,
                name text
            ) ON COMMIT DROP;
        """)

        with cur.copy("COPY temp_companies (cik, ticker, name) FROM STDIN") as copy:
            for r in rows:
                copy.write_row(r)

        cur.execute("""
            INSERT INTO companies (cik, ticker, name)
            SELECT DISTINCT ON (cik) cik, ticker, name FROM temp_companies
            ORDER BY cik, ticker
            ON CONFLICT (cik) DO UPDATE SET
                ticker = EXCLUDED.ticker,
                name = EXCLUDED.name;
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
