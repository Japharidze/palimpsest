import psycopg
import typer
from httpx import HTTPStatusError
from psycopg.rows import scalar_row
from typer import progressbar

from palimpsest.config import DATA_DIR, settings
from palimpsest.db import add_to_watchlist, upsert_change_summaries
from palimpsest.diffing import sync_changes
from palimpsest.edgar import EdgarClient
from palimpsest.ingest import (
    fetch_document,
    refresh_companies,
    sync_facts,
    sync_filings,
)
from palimpsest.llm import LLM, AnthropicLLM, OllamaLLM
from palimpsest.migrate import apply_migrations
from palimpsest.sections import extract_sections
from palimpsest.storage import LocalStorage
from palimpsest.summarize import summarize_label_changes
from palimpsest.embedding import OllamaEmbedder

app = typer.Typer(help="SEC filings research assistant", no_args_is_help=True)


def _build_llm(provider: str, model: str, anthropic_api_key: str = "") -> LLM:
    if provider == "ollama":
        return OllamaLLM(model)
    assert anthropic_api_key, "ANTHROPIC_API_KEY variable not set"
    return AnthropicLLM(model, anthropic_api_key)


@app.command("migrate")
def migrate() -> None:
    """Apply pending database migrations."""
    with psycopg.connect(settings.db_url) as conn:
        applied = apply_migrations(conn)

    for version in applied:
        typer.echo(f"applied {version}")
    if not applied:
        typer.echo("nothing to apply")


@app.command("watch")
def watch_cmd(tickers: list[str]) -> None:
    """Add companies to the watchlist by ticker."""
    tickers = [t.upper() for t in tickers]

    with psycopg.connect(settings.db_url) as conn:
        added, already, not_found = add_to_watchlist(conn, tickers)

    if added:
        typer.echo(f"added: {', '.join(added)}")
    if already:
        typer.echo(f"already watching: {', '.join(already)}")
    if not_found:
        typer.echo(f"not found: {', '.join(not_found)}")


@app.command("refresh-companies")
def refresh_companies_cmd() -> None:
    """Refresh the company/ticker mapping from EDGAR."""
    client = EdgarClient(settings.sec_user_agent)
    storage = LocalStorage(DATA_DIR)

    with psycopg.connect(settings.db_url) as conn:
        count = refresh_companies(client, storage, conn)

    typer.echo(f"{count} companies")


@app.command("sync-filings")
def sync_filings_cmd() -> None:
    """Fill document's metadata for clients in watchlist"""
    client = EdgarClient(settings.sec_user_agent)
    storage = LocalStorage(DATA_DIR)

    with psycopg.connect(settings.db_url) as conn:
        with conn.cursor(row_factory=scalar_row) as cur:
            cur.execute("select cik from watchlist")
            ciks = cur.fetchall()

        # Loop companies over the watchlist
        for cik in ciks:
            count = sync_filings(client, storage, conn, cik)
            conn.commit()
            typer.echo(f"{count} documents for client with CIK - {cik}")


@app.command("fetch-documents")
def fetch_documents_cmd() -> None:
    """Fetch documents from filings"""
    client = EdgarClient(settings.sec_user_agent)
    storage = LocalStorage(DATA_DIR)

    with psycopg.connect(settings.db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    f.cik,
                    f.accession_number,
                    f.primary_document,
                    f.document_key
                from filings f join watchlist w on f.cik = w.cik
                where f.fetched_at is null
            """)
            filings = cur.fetchall()

        count = 0
        failed = []
        for cik, accession, primary_doc, doc_key in filings:
            try:
                fetch_document(
                    client, storage, conn, cik, accession, primary_doc, doc_key
                )
                conn.commit()
                count += 1
            except HTTPStatusError as e:
                conn.rollback()
                failed.append((accession, e.response.status_code))
        typer.echo(f"{count} documents fetched for clients in watchlist")
        if failed:
            typer.echo(f"{len(failed)} failed:")
            for accession, status in failed:
                typer.echo(f"   {accession} - HTTP {status}")


@app.command("sync-facts")
def sync_facts_cmd() -> None:
    """Fill facts for clients in watchlist"""
    client = EdgarClient(settings.sec_user_agent)
    storage = LocalStorage(DATA_DIR)

    with psycopg.connect(settings.db_url) as conn:
        with conn.cursor(row_factory=scalar_row) as cur:
            cur.execute("select cik from watchlist")
            ciks = cur.fetchall()

        # Loop companies over the watchlist
        for cik in ciks:
            count = sync_facts(client, storage, conn, cik)
            conn.commit()
            typer.echo(f"{count} facts for client with CIK - {cik}")


@app.command("extract-sections")
def extract_sections_cmd() -> None:
    """Parse all fetched documents and store the text content"""
    storage = LocalStorage(DATA_DIR)

    with psycopg.connect(settings.db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    accession_number,
                    form,
                    document_key
                from filings
                where
                    fetched_at is not null
                    and parsed_at is null
            """)
            documents = cur.fetchall()

        section_count = 0
        for accn, form, key in documents:
            section_count += extract_sections(storage, conn, accn, form, key)
            conn.commit()
        typer.echo(f"{section_count} sections extracted")


@app.command("diff-sections")
def diff_sections_cmd() -> None:
    """Find differences in the last and previous submissions of each form and section"""
    with psycopg.connect(settings.db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                	distinct on
                	(f.cik,
                    f.form,
                	sfs.label)
                	f.cik,
                	f.form,
                	sfs.label,
                	sfs.accession_number,
                	sfs.content,
                	lag(sfs.accession_number) over (
                		partition by f.cik, f.form, sfs.label
                		order by f.filing_date
                	) prev_accession_number,
                	lag(sfs.content) over (
                		partition by f.cik, f.form, sfs.label
                		order by f.filing_date
                	) prev_content
                from
                	filings f
                join analytics.stg_filing_sections sfs
                	using (accession_number)
                where
                	sfs.label is not null
                order by
                	f.cik,
                    f.form,
                	sfs.label,
                	f.filing_date desc
            """)
            to_compare = cur.fetchall()

        for row in to_compare:
            count = sync_changes(conn, *row)
            conn.commit()
            typer.echo(
                f"{count} differences found for company - {row[0]}'s section of {row[2]}"
            )


@app.command("summarize-changes")
def summarize_changes_cmd() -> None:
    """Generate summary of each label change using the prefered LLM service"""
    llm = _build_llm(settings.summarizer_provider, settings.summarizer_model)
    with psycopg.connect(settings.db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    distinct on (s.text_hash)
                    s.text_hash,
                    s.label,
                    s.change_type,
                    s.from_text,
                    s.to_text
                from section_changes s
                left join change_summaries cs using (text_hash)
                where cs.text_hash is null
            """)
            changes = cur.fetchall()

        count = 0
        with progressbar(
            summarize_label_changes(llm, changes=changes), length=len(changes)
        ) as progress:
            for summary in progress:
                upsert_change_summaries(conn, summary)
                conn.commit()
                count += 1
        typer.echo(f"{count} summaries inserted")

@app.command("vectorize-sections")
def vectorize_sections_cmd():
    """Chunk -> Embed -> Store sections into table 'chunks'"""
    embedder = OllamaEmbedder(settings.embedding_model)
    with psycopg.connect(settings.db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    accession_number,
                    section,
                    content
                from filing_sections
            """)
            section_rows = cur.fetchall()

        count = 0
        with progressbar(
            vectorize_sections(embedder, section_rows), length=len(section_rows)
        ) as progress:
            for embed in progress:
                upsert_chunk(conn, embed)
                conn.commit()
                count += 1
        typer.echo(f"{count} chunks inserted")




def main() -> None:
    app()
