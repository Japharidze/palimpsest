import time
from typing import Any

import httpx


class EdgarClient:
    DATA = "https://data.sec.gov"
    WWW = "https://www.sec.gov"

    def __init__(self, user_agent: str, min_interval: float = 0.15):
        self._c = httpx.Client(headers={"User-Agent": user_agent}, timeout=30)
        self._min_interval = min_interval
        self._last = 0.0

    def _get(self, url: str) -> dict:
        wait = self._min_interval - (time.monotonic() - self._last) # Guard the min_interval time between the requests
        if wait > 0:
            time.sleep(wait)
        r = self._c.get(url)
        self._last = time.monotonic()
        r.raise_for_status()
        return r.json()

    def company_tickers(self) -> dict[str, Any]:
        url = self.WWW+"/files/company_tickers.json"
        return self._get(url=url)

    def submissions(self, cik: str) -> dict[str, Any]:
        url = f"{self.DATA}/submissions/CIK{cik}.json"
        return self._get(url=url)
