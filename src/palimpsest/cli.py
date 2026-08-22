import psycopg
import typer

from palimpsest.config import DATA_DIR, settings
from palimpsest.edgar import EdgarClient
from palimpsest.ingest import refresh_companies
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


@app.command("refresh-companies")
def refresh_companies_cmd() -> None:
    """Refresh the company/ticker mapping from EDGAR."""
    client = EdgarClient(settings.sec_user_agent)
    storage = LocalStorage(DATA_DIR)

    with psycopg.connect(settings.db_url) as conn:
        count = refresh_companies(client, storage, conn)

    typer.echo(f"{count} companies")


def main() -> None:
    app()
