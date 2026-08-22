# Palimpsest

An SEC filings research assistant. It tracks a watchlist of companies, reports what changed between their filings, and cites the exact passage behind every claim.

A palimpsest is a manuscript that was scraped clean and written over, with the earlier text still showing through — which is what a quarterly filing is. This quarter's risk factors are last quarter's, reworded. Palimpsest reads what changed.

Numbers come from XBRL and deterministic code. A language model is used only to read prose, and only for companies that rules have already flagged. Research tool, not investment advice.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose

## Setup

```bash
git clone https://github.com/<user>/palimpsest.git
cd palimpsest
cp .env.example .env      # then edit SEC_USER_AGENT
uv sync
docker compose up -d
uv run palim migrate
```

`SEC_USER_AGENT` must contain a real contact email. The SEC requires it on every request and throttles clients that omit it. No account or API key is needed.

## Usage

```bash
uv run palim migrate             # apply pending schema migrations
uv run palim refresh-companies   # load the ticker to CIK mapping from EDGAR
```

More commands land as the pipeline grows.

## How it works

Raw API responses are written to storage before anything parses them, so a parser change can be replayed without refetching. Postgres holds the parsed result. Schema changes are numbered SQL files applied in order and recorded in a `schema_migrations` table.

Read [docs/architecture.md](docs/architecture.md) for the layer-by-layer design, and [docs/decisions.md](docs/decisions.md) for the tradeoffs behind it.

## Data source

All data comes from the SEC's public [EDGAR](https://www.sec.gov/edgar) system. Filings are public domain. Access follows the SEC's fair-access policy: identify yourself in the User-Agent header and stay under 10 requests per second.
