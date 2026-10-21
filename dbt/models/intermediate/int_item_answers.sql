{{ config(materialized='view') }}
-- One row per student per question (~210M rows on the real data), never stored: marts aggregate it as it streams.
-- Each answer string has 45 letters in booklet order; area offsets map letter i to the booklet position.
-- Languages positions 1-5 depend on the foreign language the student chose (English or Spanish).
with students as (
    select * from {{ ref('int_school_results') }}
),

areas as (
    select result_id, school_id, school_state, school_type, 'LC' as area, 0 as position_offset,
           booklet_languages as booklet_id, answers_languages as answers, foreign_language
    from students
    union all
    select result_id, school_id, school_state, school_type, 'CH', 45,
           booklet_humanities, answers_humanities, null
    from students
    union all
    select result_id, school_id, school_state, school_type, 'CN', 90,
           booklet_natural_sciences, answers_natural_sciences, null
    from students
    union all
    select result_id, school_id, school_state, school_type, 'MT', 135,
           booklet_math, answers_math, null
    from students
),

answers as (
    select
        areas.*,
        letter.i,
        position_offset + letter.i as position,
        substr(answers, letter.i, 1) as given_answer,
        case when area = 'LC' and letter.i <= 5 then foreign_language end as item_language
    from areas, range(1, 46) as letter(i)
)

select
    answers.result_id,
    answers.school_id,
    answers.school_state,
    answers.school_type,
    answers.area,
    items.skill,
    answers.given_answer = items.correct_answer as is_correct
from answers
join {{ ref('stg_items') }} as items
    on  items.booklet_id = answers.booklet_id
    and items.area = answers.area
    and items.position = answers.position
    and items.foreign_language is not distinct from answers.item_language
where not items.is_annulled
