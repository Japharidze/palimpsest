create table companies (
    cik  text primary key,
    name text not null
);

create table company_tickers (
    cik    text not null references companies (cik),
    ticker text not null,
    primary key (cik, ticker)
);

create index company_tickers_ticker_idx on company_tickers (ticker);
