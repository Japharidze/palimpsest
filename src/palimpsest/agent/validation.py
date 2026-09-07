import re

ACCESSION = r"\d{10}-\d{2}-\d{6}"

# Matches a bracket holding one or more accessions and an optional label:
#   [0001045810-26-000075]
#   [0001045810-26-000075 | part_i_item_2]
#   [0001045810-25-000023 and 0001045810-25-000116 | metrics]
#   [0001045810-25-000023; 0001045810-25-000116]
CITATION_RE = re.compile(
    rf"\[\s*({ACCESSION}(?:\s*(?:,|;|and)\s*{ACCESSION})*)"
    rf"\s*(?:\|\s*([a-z0-9_ ]+?)\s*)?\]",
    re.IGNORECASE,
)

SPLIT_RE = re.compile(r"\s*(?:,|;|and)\s*", re.IGNORECASE)

# Quoted passages of at least a few words
QUOTE_RE = re.compile(r"[\"“]([^\"”]{20,})[\"”]")

# Labels that name a source rather than a filing section. A figure taken from
# the metrics tool has no section, so these are not checked against
# filing_sections.
NON_SECTION_LABELS = {"metrics", "xbrl", "financial data", "changes"}


def _parse_citations(answer: str) -> list[tuple[str, str | None]]:
    """Return (accession, label) pairs, one per accession."""
    pairs: list[tuple[str, str | None]] = []
    for accns, label in CITATION_RE.findall(answer):
        label = (label or "").strip().lower() or None
        for accn in SPLIT_RE.split(accns):
            accn = accn.strip()
            if accn:
                pairs.append((accn, label))
    return pairs


def _known_accessions(pool, accessions: list[str]) -> set[str]:
    if not accessions:
        return set()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select accession_number from filings where accession_number = any(%s)",
            (accessions,),
        )
        return {row[0] for row in cur.fetchall()}


def _known_sections(pool, accessions: list[str]) -> set[tuple[str, str]]:
    """Every (accession, section) pair, by raw key and by mapped label."""
    if not accessions:
        return set()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select s.accession_number, s.section, sl.label
            from filing_sections s
            join filings f using (accession_number)
            left join analytics.section_labels sl
                on sl.form = replace(f.form, '/A', '')
               and sl.section_key = s.section
            where s.accession_number = any(%s)
            """,
            (accessions,),
        )
        pairs: set[tuple[str, str]] = set()
        for accn, section, label in cur.fetchall():
            pairs.add((accn, section.lower()))
            if label:
                pairs.add((accn, label.lower()))
        return pairs


def _quote_found(pool, quote: str, accessions: list[str]) -> bool:
    """True if the quote appears in any cited filing, ignoring whitespace."""
    normalized = re.sub(r"[\s\u00a0]+", " ", quote).strip()
    if not normalized:
        return True
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select 1
            from filing_sections
            where accession_number = any(%s)
              and regexp_replace(content, '[\\s\\u00a0]+', ' ', 'g') ilike %s
            limit 1
            """,
            (accessions, "%" + normalized.replace("%", r"\%") + "%"),
        )
        return cur.fetchone() is not None


def check_citations(pool, answer: str) -> list[str]:
    """Return a list of problems found in an answer's citations."""
    problems: list[str] = []

    citations = _parse_citations(answer)
    if not citations:
        return ["no citations found"]

    accessions = [a for a, _ in citations]
    known = _known_accessions(pool, accessions)
    for accn in sorted(set(accessions)):
        if accn not in known:
            problems.append(f"unknown filing {accn}")

    valid = sorted(known)
    section_pairs = _known_sections(pool, valid)
    for accn, label in sorted(set(citations), key=lambda p: (p[0], p[1] or "")):
        if accn not in known or label is None:
            continue
        if label in NON_SECTION_LABELS:
            continue
        if (accn, label) not in section_pairs:
            problems.append(f"section {label!r} not found in {accn}")

    for quote in QUOTE_RE.findall(answer):
        if valid and not _quote_found(pool, quote, valid):
            snippet = quote[:60] + ("…" if len(quote) > 60 else "")
            problems.append(f'quote not found in cited filings: "{snippet}"')

    return problems
