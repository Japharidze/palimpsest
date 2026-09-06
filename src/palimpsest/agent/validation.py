import re

# Matches [0001045810-26-000075] and [0001045810-26-000075 | part_i_item_2]
CITATION_RE = re.compile(
    r"\[\s*(\d{10}-\d{2}-\d{6})\s*(?:\|\s*([a-z0-9_]+)\s*)?\]",
    re.IGNORECASE,
)

# Matches "quoted text" of at least a few words
QUOTE_RE = re.compile(r"[\"“]([^\"”]{20,})[\"”]")
 
 
def _known_accessions(conn, accessions: list[str]) -> set[str]:
    if not accessions:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            "select accession_number from filings where accession_number = any(%s)",
            (accessions,),
        )
        return {row[0] for row in cur.fetchall()}


def _known_sections(conn, pairs: list[tuple[str, str]]) -> set[tuple[str, str]]:
    if not pairs:
        return set()
    accns = [a for a, _ in pairs]
    with conn.cursor() as cur:
        cur.execute(
            """
            select accession_number, section
            from filing_sections
            where accession_number = any(%s)
            """,
            (accns,),
        )
        return {(row[0], row[1]) for row in cur.fetchall()}


def _quote_found(conn, quote: str, accessions: list[str]) -> bool:
    """True if the quote appears verbatim in any cited filing's sections."""
    normalized = re.sub(r"\s+", " ", quote).strip()
    with conn.cursor() as cur:
        cur.execute(
            """
            select 1
            from filing_sections
            where accession_number = any(%s)
              and regexp_replace(content, '\\s+', ' ', 'g') like %s
            limit 1
            """,
            (accessions, f"%{normalized}%"),
        )
        return cur.fetchone() is not None


def check_citations(conn, answer: str) -> list[str]:
    """Return a list of problems found in an answer's citations."""
    problems: list[str] = []
 
    citations = CITATION_RE.findall(answer)
    if not citations:
        return ["no citations found"]
 
    accessions = [a for a, _ in citations]
    known = _known_accessions(conn, accessions)
    for accn in set(accessions):
        if accn not in known:
            problems.append(f"unknown filing {accn}")
 
    pairs = [(a, s) for a, s in citations if s and a in known]
    known_pairs = _known_sections(conn, pairs)
    for accn, section in set(pairs):
        if (accn, section) not in known_pairs:
            problems.append(f"section {section!r} not found in {accn}")
 
    valid_accns = sorted(known)
    for quote in QUOTE_RE.findall(answer):
        if valid_accns and not _quote_found(conn, quote, valid_accns):
            snippet = quote[:60] + ("…" if len(quote) > 60 else "")
            problems.append(f'quote not found in cited filings: "{snippet}"')
 
    return problems
