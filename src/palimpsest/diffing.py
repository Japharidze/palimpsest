import hashlib
import re
from typing import NamedTuple

from rapidfuzz import fuzz, process

from palimpsest.db import upsert_section_changes


class Change(NamedTuple):
    change_type: str  # 'added' | 'removed' | 'modified'
    from_text: str | None
    to_text: str | None
    similarity: float | None  # None for added/removed
    position: int  # index in the new document; for removed, where it was

def _is_prose(p: str) -> bool:
    """Reject table rows and numeric fragments."""
    if len(p) < 40:
        return False

    digits = sum(c.isdigit() for c in p)
    if digits / len(p) > 0.15:
        return False

    words = p.split()
    if len(words) < 8:
        return False

    # a real sentence has mostly alphabetic tokens
    alpha_words = sum(1 for w in words if w.isalpha())
    return alpha_words / len(words) >= 0.6


def _paragraphs(text: str) -> list[str]:
    parts = (re.sub(r"\s+", " ", p.strip()) for p in text.split("\n"))
    return [p for p in parts if _is_prose(p)]



def _find_changes(old: str, new: str, threshold: float = 60.0) -> list[Change]:
    old_ps, new_ps = _paragraphs(old), _paragraphs(new)

    old_hashes = {hashlib.sha256(p.encode()).hexdigest() for p in old_ps}
    new_hashes = {hashlib.sha256(p.encode()).hexdigest() for p in new_ps}
    unchanged = old_hashes & new_hashes

    def h(p):
        return hashlib.sha256(p.encode()).hexdigest()

    old_left = [p for p in old_ps if h(p) not in unchanged]
    new_left = [(i, p) for i, p in enumerate(new_ps) if h(p) not in unchanged]

    changes, matched = [], set()
    for pos, para in new_left:
        best = process.extractOne(para, old_left, scorer=fuzz.token_sort_ratio)
        if best and best[1] >= threshold:
            changes.append(Change("modified", best[0], para, best[1] / 100, pos))
            matched.add(best[2])
        else:
            changes.append(Change("added", None, para, None, pos))

    for i, para in enumerate(old_left):
        if i not in matched:
            changes.append(Change("removed", para, None, None, -1))

    return changes


def sync_changes(
    conn,
    cik: str,
    form: str,
    label: str,
    accession_number: str,
    content: str,
    prev_accession_number: str,
    prev_content: str,
) -> int:
    if not prev_content: # Guarding some edge cases when section is presented first time in company's form
        return 0

    changes = _find_changes(prev_content, content)
    rows = [
        (cik, form, label, prev_accession_number, accession_number) + change
        for change in changes
    ]
    inserted = upsert_section_changes(conn, rows)
    return inserted
