from pathlib import Path

from palimpsest.config import MIGRATIONS_DIR


def apply_migrations(conn, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("""
            create table if not exists schema_migrations (
                version text primary key,
                applied_at timestamptz not null default now()
            )
        """)
        cur.execute("select version from schema_migrations")
        applied = {row[0] for row in cur.fetchall()}
    conn.commit()

    pending = sorted(p for p in migrations_dir.glob("*.sql") if p.stem not in applied)

    for path in pending:
        with conn.transaction(), conn.cursor() as cur:          # commits on exit, rolls back on exception
           cur.execute(path.read_text())
           cur.execute(
               "insert into schema_migrations (version) values (%s)", (path.stem,)
           )
    return [p.stem for p in pending]
