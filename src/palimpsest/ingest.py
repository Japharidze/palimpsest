import json
from collections.abc import Generator
from datetime import UTC, datetime

from palimpsest.db import upsert_companies, upsert_facts, upsert_filings
from palimpsest.edgar import EdgarClient

TRACKED_FORMS = frozenset({
    "10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A",
    "20-F", "20-F/A", "S-1", "S-1/A", "NT 10-K", "NT 10-Q",
})

def _parse_company(raw: dict) -> tuple[str, str, str]:
    return (str(raw['cik_str']).zfill(10), raw['ticker'], raw['title'])

def _parse_submission(raw: dict, cik: str) -> tuple[str | None, ...]:
    return (
            raw['accessionNumber'],
            cik,
            raw['form'],
            raw['filingDate'],
            raw['reportDate'] or None,
            raw['primaryDocument'],
            f"raw/companies/{cik}/filings/{raw['accessionNumber']}/{raw['primaryDocument'].replace('/', '-')}"
        )

def _parse_facts(raw: dict, cik: str) -> Generator[tuple[str | None, ...]]:
    for taxonomy, tags in raw['facts'].items():
        for tag, tag_data in tags.items():
            for unit, facts in tag_data["units"].items():
                for f in facts:
                    yield (
                        cik,
                        taxonomy,
                        tag,
                        unit,
                        f.get("start"),
                        f["end"],
                        f["val"],
                        f["accn"],
                        f.get("form"),
                        f["filed"]
                    )


def refresh_companies(client, storage, conn) -> int:
    raw = client.company_tickers()

    key = f"raw/reference/company_tickers/{datetime.now(tz=UTC).date().isoformat()}.json"
    storage.put(key, json.dumps(raw).encode())

    rows = [_parse_company(r) for r in raw.values()]
    upsert_companies(conn, rows)

    return len(rows)

def sync_filings(client: EdgarClient, storage, conn, cik) -> int:
    raw = client.submissions(cik)

    key = f"raw/companies/{cik}/submissions/{datetime.now(tz=UTC).date().isoformat()}.json"
    storage.put(key, json.dumps(raw).encode())

    recent_lists = raw['filings']['recent']

    list_of_recents = [dict(zip(recent_lists.keys(), values)) for values in zip(*recent_lists.values())]
    rows = [_parse_submission(f, cik) for f in list_of_recents if f["primaryDocument"] and f["form"] in TRACKED_FORMS]

    upsert_filings(conn, rows)

    return len(rows)

def sync_facts(client: EdgarClient, storage, conn, cik) -> int:
    raw = client.company_facts(cik)

    key = f"raw/companies/{cik}/facts/{datetime.now(tz=UTC).date().isoformat()}.json"
    storage.put(key, json.dumps(raw).encode())

    row_number = upsert_facts(conn, _parse_facts(raw, cik))

    return row_number

def fetch_documents(
    client: EdgarClient,
    storage,
    conn,
    cik: str,
    form: str,
    filing_date: datetime,
    accession_number: str,
    primary_document: str,
    document_key: str,
) -> None:
    html_bytes = client.fetch_document(cik, accession_number, primary_document)
    storage.put(document_key, html_bytes)

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE filings
            set fetched_at = %s
            where cik = %s and form = %s and filing_date = %s
        """, (datetime.now(tz=UTC), cik, form, filing_date))
