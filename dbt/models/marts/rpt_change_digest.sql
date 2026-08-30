with changes as (select * from {{ ref('rpt_section_changes') }})

select
    cik,
    company_name,
    form,
    label,
    from_accession,
    to_accession,
    to_filing_date,

    count(*) filter (where change_type = 'added')    as added,
    count(*) filter (where change_type = 'removed')  as removed,
    count(*) filter (where change_type = 'modified') as modified,
    count(*)                                          as total_changes,
    count(summary)                                    as summarized,

    min(similarity) filter (where change_type = 'modified') as lowest_similarity
from changes
group by 1,2,3,4,5,6,7
order by cik, to_filing_date desc, label
