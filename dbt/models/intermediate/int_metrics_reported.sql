with
    facts as (select * from {{ ref("int_facts_current") }}),
    tags as (select * from {{ ref("metric_tags") }})

select distinct
    on (facts.cik, facts.start_date, facts.end_date, tags.metric)
    facts.cik,
    tags.metric,
    facts.start_date,
    facts.end_date,
    facts.duration,
    facts.period_type,
    facts.val,
    facts.accn,
    facts.filed,
    false as is_derived
from facts
join tags on facts.tag = tags.tag
order by facts.cik, facts.start_date, facts.end_date, tags.metric, tags.priority
