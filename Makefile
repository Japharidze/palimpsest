include .env
export

.PHONY: db up down migrate fresh dbt dbt-seed dbt-docs psql dbt-test reset init-data sync diff summarize dump-summaries restore-summaries

up:
	docker compose up -d

down:
	docker compose down

db:
	docker compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

psql:
	PGPASSWORD=$(POSTGRES_PASSWORD) psql -h localhost -p $(POSTGRES_PORT) -U $(POSTGRES_USER) -d $(POSTGRES_DB)

migrate:
	uv run palim migrate

dbt:
	cd dbt && DBT_PROFILES_DIR=. uv run dbt seed
	cd dbt && DBT_PROFILES_DIR=. uv run dbt run
dbt-test:
	cd dbt && DBT_PROFILES_DIR=. uv run dbt test
dbt-docs:
	cd dbt && DBT_PROFILES_DIR=. uv run dbt docs generate
	cd dbt && DBT_PROFILES_DIR=. uv run dbt docs serve

reset:
	docker compose down -v
	docker compose up -d
	until docker compose exec -T postgres pg_isready -U $(POSTGRES_USER) -q; do sleep 1; done
	$(MAKE) migrate

init-data:
	uv run palim refresh-companies
	uv run palim watch NVDA MSFT GOOGL LLY KO JPM ASML RDDT

sync:
	uv run palim sync-filings
	uv run palim sync-facts
	uv run palim fetch-documents
	uv run palim extract-sections

diff:
	uv run palim diff-sections

summarize:
	uv run palim summarize-changes

fresh:
	$(MAKE) dump-summaries
	$(MAKE) reset
	$(MAKE) init-data sync dbt
	$(MAKE) diff
	$(MAKE) restore-summaries
	$(MAKE) summarize


dump-summaries:
	docker compose exec -T postgres pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) \
		-t change_summaries --data-only > data/summaries.sql || true

restore-summaries:
	docker compose exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) \
		< data/summaries.sql || true
