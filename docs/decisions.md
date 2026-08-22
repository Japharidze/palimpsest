# Decisions

A running log of design decisions, why they were made, and what they cost.

---

## 1. One row per company, keyed by CIK

**Decision.** `companies` has CIK as the primary key. Where a filer has several tickers (share classes, preferred series), one is chosen deterministically and the rest are dropped.

**Why.** CIK is what filings, facts, and the watchlist all key on. A `(cik, ticker)` grain would make CIK non-unique and force every downstream join to be careful.

**Cost.** Real, and visible. The source has about 10,400 rows and the table holds about 8,000 — the difference is share classes. Looking up a company by a ticker that lost the tie-break returns nothing.

---

## 2. Ingestion tracks progress with per-stage timestamps

**Decision.** Each ingested record carries a nullable timestamp per pipeline stage (fetched, parsed, embedded) rather than a single status column.

**Why.** Stages complete independently and are not strictly ordered. "What still needs parsing" is a query on one column, so each stage is separately resumable and a failure in one does not force redoing the others. The timestamps also show how long each stage takes.

**Cost.** Nothing enforces consistency between columns — a row can claim to be embedded but not parsed. A check constraint would fix it if it ever matters.

