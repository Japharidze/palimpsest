select
  s.accession_number,
  f.form,
  l.label,
  s.section,
  s.content,
  s.start_offset,
  s.end_offset,
  s.char_count,
  s.confidence,
  s.detection_method
from {{ source('raw', 'filing_sections') }} s
join {{ source('raw', 'filings') }} f using (accession_number)
left join {{ ref('section_labels') }} l
  on l.form = replace(f.form, '/A', '')
  and l.section_key = s.section
