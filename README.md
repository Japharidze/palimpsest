# Palimpsest

An SEC filings research assistant. It tracks a watchlist of companies, reports what changed between their filings, and cites the exact passage behind every claim.

A palimpsest is a manuscript that was scraped clean and written over, with the earlier text still showing through — which is what a quarterly filing is. This quarter's risk factors are last quarter's, reworded. Palimpsest reads what changed.

Numbers come from XBRL and deterministic code. A language model is used only to read prose, and only for companies that rules have already flagged. Research tool, not investment advice.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose
- [Ollama](https://ollama.com) for local summarization and embeddings, with the
  models named in `.env` pulled beforehand
- An Anthropic API key, if the agent is configured to use it

## Setup

```bash
git clone https://github.com/<user>/palimpsest.git
uv run palim migrate             # apply pending schema migrations
uv run palim refresh-companies   # load the ticker to CIK mapping from EDGAR
uv run palim watch NVDA MSFT     # add companies to the watchlist
uv run palim sync-filings        # index each watched company's filings
uv run palim sync-facts          # load XBRL facts
make dbt                         # build the metric models
make dbt-test                    # run data quality tests
cd palimpsest
cp .env.example .env      # then edit SEC_USER_AGENT
uv sync
make fresh
```

`make fresh` starts Postgres, applies migrations, loads the watchlist, syncs filings and XBRL facts from EDGAR, and builds the dbt models.

`SEC_USER_AGENT` must contain a real contact email. The SEC requires it on every request and throttles clients that omit it. No account or API key is needed.

## Usage

```bash
uv run palim migrate             # apply pending schema migrations
uv run palim refresh-companies   # load the ticker to CIK mapping from EDGAR
uv run palim watch NVDA MSFT     # add companies to the watchlist
uv run palim sync-filings        # index each watched company's filings
uv run palim sync-facts          # load XBRL facts
uv run palim fetch-documents     # download filing documents
uv run palim extract-sections    # split documents into labelled sections
uv run palim diff-sections       # find paragraph-level changes between filings
uv run palim summarize-changes   # describe each change with a language model
uv run palim vectorize-sections  # chunk and embed sections for retrieval
make dbt                         # build the metric models
make dbt-test                    # run data quality tests
```

## How it works

Raw API responses are written to storage before anything parses them, so a parser change can be replayed without refetching. Postgres holds the parsed result. Schema changes are numbered SQL files applied in order and recorded in a `schema_migrations` table. dbt turns raw XBRL facts into per-quarter and per-year metrics with ratios, growth rates, and red-flag columns.

Read [docs/architecture.md](docs/architecture.md) for the layer-by-layer design, and [docs/decisions.md](docs/decisions.md) for the tradeoffs behind it.

## Limitations

- **US GAAP only.** The tag-to-metric mapping covers `us-gaap`. IFRS filers are not mapped.
- **Share classes.** A filer with several tickers keeps one; looking up a company by a ticker that lost the tie-break returns nothing.
- **Annual-only filers.** Foreign private issuers file 20-F and no 10-Q, so they appear in the yearly metrics and not the quarterly ones.
- **Ticker resolution.** After a restructuring a ticker can point at a newly registered entity whose filing history sits under a predecessor CIK.
- **Foreign private issuers.** Section detection on 20-F filings is inconsistent
  across years, so those filings are excluded from language diffing. Their
  financial metrics are unaffected.
- **Table-heavy sections.** Financial statements change in every figure every
  quarter, so they are indexed and searchable but not diffed.
- **Small local models.** Models below roughly 8B parameters do not reliably
  compose multiple tools or follow citation instructions. The agent is intended
  to run against a hosted model; local models are for development.

## Data source

All data comes from the SEC's public [EDGAR](https://www.sec.gov/edgar) system. Filings are public domain. Access follows the SEC's fair-access policy: identify yourself in the User-Agent header and stay under 10 requests per second.
