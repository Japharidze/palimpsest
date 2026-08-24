select q.cik, q.period_end
from {{ ref('fct_company_quarter') }} q
join {{ source('raw', 'watchlist') }} w on w.cik = q.cik
where q.period_end >= current_date - interval '2 years'
  and q.revenue is null
  -- 20-F filers report annually; quarterly coverage is expected to be empty
  and exists (
      select 1 from {{ source('raw', 'filings') }} f
      where f.cik = q.cik and f.form = '10-Q'
  )
