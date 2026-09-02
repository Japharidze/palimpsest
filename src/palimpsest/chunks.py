from collections.abc import Generator
from datetime import date

from langchain_text_splitters import RecursiveCharacterTextSplitter
from psycopg.rows import dict_row

from palimpsest.embedding import Embedder


def _get_chunks(text: str) -> list[tuple[tuple, str]]:
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""],
        chunk_size=750,
        chunk_overlap=200,
        is_separator_regex=False,
        add_start_index=True,
    )
    chunks = splitter.create_documents(texts=[text])

    result = []
    for chunk in chunks:
        content = chunk.page_content
        start_offset = chunk.metadata["start_index"]
        end_offset = start_offset + len(content)
        result.append(((start_offset, end_offset), content))
    return result


def vectorize_sections(
    embedder: Embedder, accn: str, section: str, content: str
) -> Generator[tuple]:
    for idx, ((start_offset, end_offset), chunk) in enumerate(_get_chunks(content)):
        assert content[start_offset:end_offset] == chunk, (
            "Chunk doesn't correspond to offset range"
        )
        yield (
            accn,
            section,
            idx,
            start_offset,
            end_offset,
            chunk,
            embedder.embed(chunk),
        )


def search(
    conn,
    embedder: Embedder,
    text: str,
    ticker: str | None = None,
    form: str | None = None,
    section: str | None = None,
    since: date | None = None,
    limit: int = 15,
) -> list[dict]:
    query = """
        with ranked as (
            select
                sc.accession_number,
                sc.section,
                sc.start_offset,
                sc.end_offset,
                sc.content,
                f.cik,
                f.form,
                f.filing_date,
                sc.embedding <=> %(vec)s::vector as distance,
                row_number() over (
                    partition by sc.accession_number, sc.section
                    order by sc.embedding <=> %(vec)s::vector
                ) as rn
            from section_chunks sc
            join filings f using (accession_number)
            left join analytics.section_labels sl
                on sl.form = replace(f.form, '/A', '')
               and sl.section_key = sc.section
            where
                (%(ticker)s::text is null or f.cik in (
                    select cik from company_tickers where ticker = %(ticker)s
                ))
                and (%(form)s::text is null or f.form = %(form)s)
                and (%(section)s::text is null
                    or sl.label = %(section)s
                    or sc.section = %(section)s)
                and (%(since)s::date is null or f.filing_date >= %(since)s)
        ), deduped as (
            select distinct on (left(content, 200))
                accession_number, section, cik, form, filing_date,
                start_offset, end_offset, content, distance
            from ranked
            where rn <= %(per_section)s
            order by left(content, 200), filing_date desc
        )
        select * from deduped
        order by distance
        limit %(limit)s
    """
    vector = embedder.embed(text)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, {
                "vec": vector,
                "ticker": ticker,
                "form": form,
                "section": section,
                "since": since,
                "per_section": 3,
                "limit": limit
            })
        nearest_chunks = cur.fetchall()

    return nearest_chunks
