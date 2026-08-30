create table if not exists section_changes (
    cik            text    not null references companies (cik),
    form           text    not null,
    label          text,
    from_accession text    not null references filings (accession_number),
    to_accession   text    not null references filings (accession_number),
    change_type    text    not null,
    from_text      text,
    to_text        text,
    similarity     numeric,
    position       int,
    text_hash      text generated always as (
        md5(coalesce(from_text, '') || '||' || coalesce(to_text, ''))
    ) stored
);

create index if not exists section_changes_lookup_idx
    on section_changes (cik, form, label, to_accession);

create index if not exists section_changes_hash_idx
    on section_changes (text_hash);


create table if not exists change_summaries (
    text_hash  text primary key,
    summary    text        not null,
    model      text        not null,
    created_at timestamptz not null default now()
);
