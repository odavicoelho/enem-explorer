-- INEP publishes each booklet's answer key twice: as a string in the results file and as rows in the
-- items file. They must agree everywhere, or the per-question analysis would be wrong.
with keys as (
    select distinct booklet_math as booklet_id, 'MT' as area, 135 as position_offset, key_math as answer_key
    from {{ ref('stg_results') }} where key_math is not null
    union all
    select distinct booklet_humanities, 'CH', 45, key_humanities
    from {{ ref('stg_results') }} where key_humanities is not null
),

letters as (
    select booklet_id, area, position_offset + i as position, substr(answer_key, i, 1) as key_letter
    from keys, range(1, 46) as t(i)
)

select letters.*, items.correct_answer
from letters
join {{ ref('stg_items') }} as items using (booklet_id, area, position)
where items.correct_answer != letters.key_letter
