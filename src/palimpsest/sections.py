from datetime import UTC, datetime

from edgar.documents import ParserConfig, parse_html

from palimpsest.db import upsert_sections
from palimpsest.storage import LocalStorage

SECTIONS = {"part_i_item_1a": "risk_factors", "part_ii_item_7": "mda"}


def extract_sections(storage: LocalStorage, conn, accn, form, key) -> int:
    doc = parse_html(storage.get(key).decode(), ParserConfig(form=form))
    rows = []
    for name, label in SECTIONS.items():
        section = doc.sections.get(name)
        if section:
            rows.append(
                (
                    accn,
                    label,
                    section.text(),
                    section.start_offset,
                    section.end_offset,
                    section.confidence,
                    section.detection_method
                )
            )

    inserted_count = upsert_sections(conn, rows)
    with conn.cursor() as cur:
        cur.execute("""
           UPDATE filings
           set parsed_at = %s
           where accession_number = %s
        """, (datetime.now(tz=UTC), accn))
    return inserted_count
