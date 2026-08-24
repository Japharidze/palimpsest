with
    q as (select * from {{ ref("fct_company_quarter") }}),
    c as (select cik, name from {{ source("raw", "companies") }}),

    base as (
        select
            q.cik,
            c.name as company_name,
            q.period_end,

            q.revenue,
            q.cost_of_revenue,
            q.net_income,
            q.operating_cash_flow,
            q.total_assets,
            q.stockholders_equity,
            q.inventory,
            q.receivables,
            q.cash,
            q.revenue_is_derived,

            -- ratios
            case
                when q.revenue > 0 then (q.revenue - q.cost_of_revenue) / q.revenue
            end as gross_margin,

            -- averaged denominators for return ratios
            (q.total_assets + lag(q.total_assets) over w) / 2 as avg_assets,
            (q.stockholders_equity + lag(q.stockholders_equity) over w)
            / 2 as avg_equity,

            lag(q.revenue, 4) over w as revenue_yoy_prior,
            lag(q.inventory, 4) over w as inventory_yoy_prior,
            lag(q.receivables, 4) over w as receivables_yoy_prior
        from q
        join c on c.cik = q.cik
        window w as (partition by q.cik order by q.period_end)
    ),

    ratios as (
        select
            *,
            case when avg_assets > 0 then net_income / avg_assets end as roa,
            case when avg_equity > 0 then net_income / avg_equity end as roe,
            case
                when revenue_yoy_prior > 0 then revenue / revenue_yoy_prior - 1
            end as revenue_growth_yoy,
            case
                when inventory_yoy_prior > 0 then inventory / inventory_yoy_prior - 1
            end as inventory_growth_yoy,
            case
                when receivables_yoy_prior > 0
                then receivables / receivables_yoy_prior - 1
            end as receivables_growth_yoy,
            case
                when operating_cash_flow < 0 and operating_cash_flow is not null
                then cash / abs(operating_cash_flow)
            end as runway_quarters
        from base
    )

select
    *,
    gross_margin - lag(gross_margin, 4) over w as gross_margin_yoy_delta,
    roa - lag(roa, 4) over w as roa_yoy_delta,
    roe - lag(roe, 4) over w as roe_yoy_delta,

    -- flags
    coalesce(
        gross_margin - lag(gross_margin, 4) over w < -0.02, false
    ) as flag_margin_compression,
    coalesce(
        inventory_growth_yoy - revenue_growth_yoy > 0.10, false
    ) as flag_inventory_buildup,
    coalesce(
        receivables_growth_yoy - revenue_growth_yoy > 0.10, false
    ) as flag_receivables_buildup,
    coalesce(roa - lag(roa, 4) over w < -0.01, false) as flag_roa_deterioration,
    coalesce(runway_quarters < 4, false) as flag_short_runway
from ratios
window w as (partition by cik order by period_end)
order by cik, period_end desc
