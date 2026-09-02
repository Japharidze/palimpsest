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
