with source as (select * from {{ ref("stg_xbrl_facts") }})

select distinct
    on (cik, taxonomy, tag, unit, start_date, end_date)
    cik,
    taxonomy,
    tag,
    unit,
    start_date,
    end_date,
    duration,
    period_type,
    val,
    accn,
    form,
    filed
from source
order by cik, taxonomy, tag, unit, start_date, end_date, filed, accn desc
