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

### 7. Filing sections come from a library, not a parser we wrote

**Decision.** Section extraction uses `edgartools`, which detects sections from
a filing's table of contents and reports a confidence score for each. An earlier
hand-written extractor was measured and discarded.

**Why.** Filing HTML has no semantic structure. Section headings are marked by
visual formatting, appear again in the table of contents and in
cross-references, and differ by filing agent and by year. The hand-written
version worked on the filings it was tuned against and broke on the next one;
every fix made it fit one company more closely. Section extraction is a solved
commodity, and the parts of this project worth building are elsewhere.

**Cost.** A dependency on one maintainer for a format the SEC keeps amending.
Section keys are inconsistent across form types — annual reports use readable
names, quarterly reports use positional ones — so a mapping is needed to query
across forms. Detection on foreign private issuers is unreliable enough that
those filings are excluded from language diffing.

---

### 8. Changes are found by code and explained by a model

**Decision.** Paragraphs are hashed to skip unchanged text, then remaining ones
are matched by fuzzy similarity to separate rewordings from genuine additions
and removals. Only the changed paragraphs are sent to a model, one at a time,
for a one-sentence description of what changed.

**Why.** Asking a model what changed between two long sections means holding
both in context, paying for every token on every run, and receiving an answer
that cannot be traced to a position in either document. Finding the change is
mechanical and exact. Saying what it means is the part a model is good at, and
it only needs the few hundred characters that actually differ.

**Cost.** Similarity matching is greedy, so a paragraph pair is matched to the
best available candidate rather than the globally optimal one. Sections that are
mostly tables produce a change for every figure that moved, so they are excluded
from diffing; that also means numeric commentary inside them is not covered.

---

### 9. Summaries are addressed by content, not by row

**Decision.** Each summary is keyed on a hash of the paragraph text it
describes, in a table separate from the changes themselves.

**Why.** Re-running the diff with different settings produces a different set of
rows. Keying summaries on those rows would orphan every summary whenever the
diff changed, and re-generating them costs hours of inference. Keyed on content,
a summary survives any re-run, and the same table doubles as the cache that stops
the same text being summarized twice.

**Cost.** A summary can outlive the change it describes, so the table accumulates
rows nothing references.

---

### 10. Retrieval returns passages, and one passage per repeat

**Decision.** Filing sections are split into overlapping chunks with character
offsets, embedded, and stored in the same database as everything else. Search
caps how many chunks one section may contribute and collapses chunks whose
opening text is identical, keeping the most recent.

**Why.** Companies repeat boilerplate verbatim for years, so ranking by
similarity alone returns the same paragraph from a dozen filings and crowds out
everything else. Offsets are stored because an answer has to point at a position
in a filing, not merely quote text that resembles it.

**Cost.** Deduplication is by matching text, so a reworded repeat survives as a
separate result — arguably correct, since a reworded disclosure is a different
disclosure, but it means near-duplicates still appear. Changing the embedding
model invalidates every stored vector.

---

### 11. A custom model abstraction was built, then replaced

**Decision.** Model access initially went through a small in-house interface so
providers could be swapped. Once the agent needed a second provider, that
interface was replaced with LangChain's.

**Why.** The in-house version handled one provider cleanly and made the seam
visible, which was the point of writing it. Supporting a second one meant
normalising message shapes, tool schemas and tool-result formats — work that an
existing library already does, and does better. Keeping both meant friction at
every boundary between them.

**Cost.** A dependency on a fast-moving library whose API has changed
repeatedly. Domain code — ingestion, storage, transformation, diffing, chunking,
search — deliberately stays outside it.
