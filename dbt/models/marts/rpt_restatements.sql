with
    facts as (select * from {{ ref("stg_xbrl_facts") }}),
    tags as (select * from {{ ref("metric_tags") }}),
    c as (select cik, name from {{ source("raw", "companies") }}),

    versions as (
        select
            facts.cik,
            tags.metric,
            facts.start_date,
            facts.end_date,
            count(distinct facts.val) as version_count,
            min(facts.val) as first_val,
            max(facts.val) as last_val,
            max(facts.filed) as last_filed
        from facts
        join tags on facts.tag = tags.tag
        where facts.taxonomy = 'us-gaap'
        group by 1, 2, 3, 4
        having count(distinct facts.val) > 1
    )

select
    v.cik,
    c.name as company_name,
    v.metric,
    v.start_date,
    v.end_date,
    v.version_count,
    v.first_val,
    v.last_val,
    v.last_val - v.first_val as change_amount,
    case
        when v.first_val <> 0 then (v.last_val - v.first_val) / abs(v.first_val)
    end as change_pct,
    v.last_filed
from versions v
join c on c.cik = v.cik
order by
    abs(
        case
            when v.first_val <> 0 then (v.last_val - v.first_val) / abs(v.first_val)
        end
    ) desc nulls last
