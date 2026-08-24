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

---

## 3. Every reported version of a figure is kept

**Decision.** The fact table stores each figure once per filing that reported it. A separate model picks the most recently filed value for metrics; the full history stays behind it.

**Why.** Companies re-report prior periods as comparatives, and sometimes the number changes. Keeping only the latest makes the metrics correct but makes restatement detection impossible. Keeping everything gives both.

**Cost.** Roughly half the rows are repeats — about 205,000 facts collapse to 105,000 distinct figures. Anything querying the fact table directly must deduplicate or it double-counts.

---

## 4. Tag-to-metric mapping is hand-maintained

**Decision.** A CSV maps XBRL tags to metric names with a priority per tag. Where a company reports several mapped tags for one period, the highest priority wins.

**Why.** Deciding that a given tag means "revenue" is an accounting judgment, not a pattern match. Tags also change over time and differ by industry — a bank's top line is a different tag from a manufacturer's. Guessing produces confidently wrong numbers, which is the failure the deterministic layer exists to prevent.

**Cost.** Adding a company can require adding mappings. A test flags recent quarters with a missing core metric so the gap surfaces rather than sitting silently as a null.

---

## 5. Fourth-quarter flows are derived and marked

**Decision.** Most filers report the fourth quarter only inside the annual figure. Where three quarters and an annual figure exist, the fourth is computed as the difference and flagged as derived.

**Why.** Without it a quarter in four is missing, always the year-end one. Flagging it keeps a computed number from being presented with the same confidence as a reported one.

**Cost.** Only fires when exactly three quarters are present. A company reporting an unusual number of interim periods gets no derived quarter.

---

## 6. Annual-only filers get their own table

**Decision.** Quarterly and yearly metrics are separate tables at separate grains.

**Why.** Foreign private issuers file an annual report and no quarterly ones, so they have no quarterly data at all. Mixing grains in one table would mean every query has to filter correctly or risk comparing a quarter against a year.

**Cost.** Two tables to keep in step, and anything wanting both has to query both.
