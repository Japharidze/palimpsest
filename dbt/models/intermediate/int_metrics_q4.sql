with
    metrics as (select * from {{ ref('int_metrics_reported') }}),

    annual as (
        select cik, metric, start_date, end_date, val, accn, filed
        from metrics
        where period_type = 'year'
    ),

    combined as (
        select
            a.cik,
            a.metric,
            a.start_date  as fy_start,
            a.end_date    as fy_end,
            a.val         as annual_val,
            a.accn,
            a.filed,
            sum(q.val)    as quarters_sum,
            count(q.val)  as quarters_found,
            max(q.end_date) as last_quarter_end
        from annual a
        join metrics q
          on  q.cik         = a.cik
          and q.metric      = a.metric
          and q.period_type = 'quarter'
          and q.start_date >= a.start_date
          and q.end_date   <= a.end_date
        group by 1,2,3,4,5,6,7
    )

select
    cik,
    metric,
    last_quarter_end + 1        as start_date,
    fy_end                      as end_date,
    fy_end - last_quarter_end   as duration,
    'quarter'                   as period_type,
    annual_val - quarters_sum   as val,
    accn,
    filed,
    true                        as is_derived
from combined
where quarters_found = 3
