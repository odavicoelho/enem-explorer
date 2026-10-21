-- The base for every ranking: students linked to a school who took all four exams and have an essay score.
-- (Only students finishing high school that year have a school in the data.)
select
    *,
    ({{ score_columns() | join(' + ') }}) / 5 as score_overall
from {{ ref('stg_results') }}
where school_id is not null
  and present_all_exams
  and score_essay is not null
