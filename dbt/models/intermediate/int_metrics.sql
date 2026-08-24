with
    reported as (select * from {{ ref("int_metrics_reported") }}),
    q4 as (select * from {{ ref("int_metrics_q4") }})

select *
from reported
union all
select *
from q4
