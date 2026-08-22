def upsert_companies(conn, rows):
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
            ON CONFLICT (cik) DO UPDATE SET
                ticker = EXCLUDED.ticker,
                name = EXCLUDED.name;
        """)
