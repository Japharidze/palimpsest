select s.*, l.label
from {{ source('raw', 'filing_sections') }} s
join {{ source('raw', 'filings') }} f using (accession_number)
left join {{ ref('section_labels') }} l
  on l.form = replace(f.form, '/A', '')
  and l.section_key = s.section
