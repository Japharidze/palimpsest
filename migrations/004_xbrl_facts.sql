create table if not exists xbrl_facts (
    cik        text    not null references companies (cik),
    taxonomy   text    not null,
    tag        text    not null,
    unit       text    not null,
    start_date date,
    end_date   date    not null,
    duration   integer generated always as (end_date - start_date) stored,
    val        numeric not null,
    accn       text    not null,
    form       text,
    filed      date    not null,
    constraint xbrl_facts_uq unique nulls not distinct
        (cik, taxonomy, tag, unit, accn, end_date, start_date)
);

create index if not exists xbrl_facts_lookup_idx
    on xbrl_facts (cik, tag, end_date desc);
