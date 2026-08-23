include .env
export

.PHONY: db up down migrate fresh

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
	cd dbt && DBT_PROFILES_DIR=. uv run dbt run
dbt-seed:
	cd dbt && DBT_PROFILES_DIR=. uv run dbt seed
dbt-test:
	cd dbt && DBT_PROFILES_DIR=. uv run dbt test

reset:
	docker compose down -v
	docker compose up -d
	until docker compose exec -T postgres pg_isready -U $(POSTGRES_USER) -q; do sleep 1; done
	$(MAKE) migrate

seed:
	uv run palim refresh-companies
	uv run palim watch NVDA MSFT GOOGL LLY KO XOM JPM ASML RDDT

sync:
	uv run palim sync-filings
	uv run palim sync-facts

fresh: reset seed sync
