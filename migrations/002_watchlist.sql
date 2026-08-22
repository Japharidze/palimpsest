create table if not exists watchlist (
    cik text primary key references companies (cik) on delete restrict,
    created_at timestamptz not null default now()
)
