create table if not exists filing_sections (
    accession_number text not null references filings (accession_number),
    section text not null,
    content text not null,
    start_offset int not null,
    end_offset int not null,
    confidence numeric not null,
    detection_method text not null,
    char_count int generated always as (char_length(content)) stored,
    primary key (accession_number, section)
);
