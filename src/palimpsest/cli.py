import psycopg
import typer

from palimpsest.config import settings
from palimpsest.migrate import apply_migrations

app = typer.Typer(help="SEC filings research assistant")


@app.command()
def migrate() -> None:
    """Apply pending database migrations."""
    with psycopg.connect(settings.db_url) as conn:
        applied = apply_migrations(conn)

    if applied:
        for version in applied:
            typer.echo(f"applied {version}")
    else:
        typer.echo("nothing to apply")


def main() -> None:
    app()
