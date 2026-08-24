with source as (
    select * from {{ source('raw', 'xbrl_facts') }}
)

select
    cik,
    taxonomy,
    tag,
    unit,
    start_date,
    end_date,
    duration,
    case
        when start_date is null then 'instant'
        when duration between 80 and 100 then 'quarter'
        when duration between 350 and 380 then 'year'
        when duration between 170 and 200 then 'half_year'
        else 'other'
    end as period_type,
    val,
    accn,
    form,
    filed
from source
