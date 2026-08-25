import psycopg
import typer
from psycopg.rows import scalar_row

from palimpsest.config import DATA_DIR, settings
from palimpsest.db import add_to_watchlist
from palimpsest.edgar import EdgarClient
from palimpsest.ingest import (
    fetch_documents,
    refresh_companies,
    sync_facts,
    sync_filings,
)
from palimpsest.migrate import apply_migrations
from palimpsest.storage import LocalStorage

app = typer.Typer(
        help="SEC filings research assistant",
        no_args_is_help=True
        )


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
                    f.form,
                    f.filing_date,
                    f.accession_number,
                    f.primary_document,
                    f.document_key
                from filings f join watchlist w on f.cik = w.cik
                where f.fetched_at is null
            """)
            filings = cur.fetchall()

        count = 0
        for filing in filings:
            fetch_documents(client, storage, conn, *filing)
            conn.commit()
            count += 1
        typer.echo(f"{count} documents fetched for clients in watchlist")

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


def main() -> None:
    app()
