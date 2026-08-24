select cik, period_end
from {{ ref("fct_company_quarter") }}
group by 1, 2
having count(*) > 1
