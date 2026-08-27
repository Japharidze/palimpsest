create table if not exists section_changes (
    cik text not null references companies (cik),
    form text not null,
    label text,
    from_accession text not null references filings(accession_number),
    to_accession text not null references filings(accession_number),
    change_type text not null,
    from_text text,
    to_text text,
    similarity numeric,
    position int
)
