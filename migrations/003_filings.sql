create table if not exists filings (
    accession_number text primary key,
    cik              text not null references companies (cik),
    form             text not null,
    filing_date      date not null,
    report_date      date,
    primary_document text,
    document_key     text,
    fetched_at       timestamptz,
    parsed_at        timestamptz
);

create index if not exists filings_cik_form_date_idx
    on filings (cik, form, filing_date desc);
