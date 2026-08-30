with
    changes   as (select * from {{ source('raw', 'section_changes') }}),
    summaries as (select * from {{ source('raw', 'change_summaries') }}),
    companies as (select cik, name from {{ source('raw', 'companies') }}),
    filings   as (select accession_number, filing_date, report_date
                  from {{ source('raw', 'filings') }})

select
    c.cik,
    co.name as company_name,
    c.form,
    c.label,

    c.from_accession,
    c.to_accession,
    pf.filing_date as from_filing_date,
    tf.filing_date as to_filing_date,

    c.change_type,
    c.position,
    c.similarity,
    c.from_text,
    c.to_text,
    s.summary,
    s.model as summary_model

from changes c
join companies co on co.cik = c.cik
join filings pf on pf.accession_number = c.from_accession
join filings tf on tf.accession_number = c.to_accession
left join summaries s on s.text_hash = c.text_hash
order by c.cik, tf.filing_date desc, c.label, c.position
