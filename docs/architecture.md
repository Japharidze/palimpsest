# Architecture

Palimpsest reads SEC filings and reports what changed. Numbers come from structured data and deterministic code; a language model is used only to read prose, and only for companies that deterministic rules have already flagged as interesting.

## Principles

**Anything that must be correct is computed, not generated.** Financial figures, quarter-over-quarter comparisons, red-flag rules, and ranking are ordinary code over a warehouse. A language model cannot silently change a margin calculation.

**The model reads, it does not decide.** Risk factors, MD&A, and language diffs are unstructured prose. That is where a model earns its cost. Everything it produces must carry a citation to a specific passage in a specific filing.

**Cheap work gates expensive work.** Rules run across the whole watchlist for effectively nothing. Only companies that trip a rule are escalated to model analysis. This keeps cost proportional to what is actually happening rather than to the size of the watchlist.

**Raw responses are never discarded.** EDGAR serves current state, not history. Every response is stored before parsing so a parser change can be replayed against the original bytes.

## Pipeline

![](pipeline.svg)

Raw storage sits between ingestion and the database: responses are written to disk first, and Postgres is populated by parsing what was stored. A parser change is replayed from storage without refetching.

The arrow from the rule engine to the agent is the one that matters. Rules do not only produce flags for display — they decide which companies are worth spending tokens on.

## Layers

**Ingestion.** A throttled EDGAR client fetches the ticker-to-CIK mapping, per-company filing indexes, and XBRL company facts. Every response is written to storage under a dated key before parsing. Reruns are idempotent: records are upserted on their natural key, and progress through the pipeline is tracked with a nullable timestamp per stage, so any stage can be resumed independently.

**Warehouse.** Postgres holds parsed filing metadata, XBRL facts, extracted filing sections, and chunk embeddings via pgvector. Raw documents stay in storage; only what is queried lives in the database.

**Transform.** dbt turns raw facts into metrics in five steps: staging types and classifies each fact's period as an instant, a quarter, or a year; a deduplication model reduces every re-reported figure to its most recently filed version; a seed maps XBRL tags to metric names by priority; fourth-quarter flows absent from the filings are derived from the annual figure and marked as derived; and the results are pivoted into a quarterly and a yearly table, one row per company per period. Two report tables sit on top — one carrying ratios, growth rates, and red-flag columns, the other listing periods whose reported value changed between filings. dbt tests cover grain, nulls, and metric coverage, so a company reporting under an unmapped tag surfaces as a failure rather than a silent null.

**Rules.** Plain Python over the report tables. Going-concern language, auditor changes, late filings, restatements, metric deterioration. Deterministic, testable, and the input to triage.

**Text.** Filing documents are downloaded once and parsed from storage, so a
parser change is replayed without refetching. Sections are extracted with a
confidence score, split into overlapping chunks with character offsets, and
embedded into the same database as the rest of the data. Consecutive filings of
the same form are compared paragraph by paragraph: unchanged text is skipped by
hash, and the remainder is matched by similarity to distinguish rewordings from
additions and removals. Each change is then described by a language model in a
single sentence, keyed on the hash of the text it describes so the result
survives any re-run of the diff.
 
**Agent.** A LangGraph state machine. One node calls the model with the
available tools; a conditional edge routes to a tool node when the model asks
for one, and to the end when it answers. Tools are ordinary functions over the
warehouse — passage search, company metrics, recent changes — and the model
never touches the database: it emits a name and arguments, and the calling code
holds the only mapping to behaviour. Conversation state persists per thread, so
follow-up questions carry their history. Citation checking is mechanical first —
every claimed passage must exist at the offset it claims, in the filing it
claims — before any model-based critique. A model judging a model is not
evidence.
