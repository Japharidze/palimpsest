import json
from datetime import UTC, datetime

from palimpsest.db import upsert_companies


def _parse_company(raw: dict) -> tuple[str, str, str]:
    return (str(raw['cik_str']).zfill(10), raw['ticker'], raw['title'])

def refresh_companies(client, storage, conn) -> int:
    raw = client.company_tickers()

    key = f"raw/reference/company_tickers/{datetime.now(tz=UTC).date().isoformat()}.json"
    storage.put(key, json.dumps(raw).encode())

    rows = [_parse_company(r) for r in raw.values()]
    upsert_companies(conn, rows)

    return len(rows)

