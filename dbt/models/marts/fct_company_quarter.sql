with
    metrics as (
        select *
        from {{ ref("int_metrics") }}
        where period_type in ('quarter', 'instant')
    )

select
    cik,
    end_date as period_end,

    -- flows (quarterly durations)
    max(val) filter (where metric = 'revenue') as revenue,
    bool_or(is_derived) filter (where metric = 'revenue')  as revenue_is_derived,
    max(val) filter (where metric = 'cost_of_revenue') as cost_of_revenue,
    bool_or(is_derived) filter (where metric = 'cost_of_revenue')  as cost_of_revenue_is_derived,
    max(val) filter (where metric = 'net_income') as net_income,
    bool_or(is_derived) filter (where metric = 'net_income') as net_income_is_derived,
    max(val) filter (where metric = 'operating_cash_flow') as operating_cash_flow,
    bool_or(is_derived) filter (where metric = 'operating_cash_flow') as operating_cash_flow_is_derived,

    -- balances (instants)
    max(val) filter (where metric = 'total_assets') as total_assets,
    max(val) filter (where metric = 'stockholders_equity') as stockholders_equity,
    max(val) filter (where metric = 'inventory') as inventory,
    max(val) filter (where metric = 'receivables') as receivables,
    max(val) filter (where metric = 'cash') as cash,

    max(filed) as last_filed
from metrics
group by cik, end_date
