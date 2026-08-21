create table if not exists companies (
    cik            text        primary key,
    ticker         text        not null,
    name           text        not null,
    last_seen_at   timestamptz not null default now()
);

create index if not exists companies_ticker_idx on companies (ticker);
