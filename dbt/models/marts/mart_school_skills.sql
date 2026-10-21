-- Per published school: % correct per skill, compared with schools of the same type in the same state.
with school_skills as (
    select school_id, area, skill, count(*) as answers, round(100 * avg(is_correct::int), 1) as pct_correct
    from {{ ref('int_item_answers') }}
    where school_id in (select school_id from {{ ref('mart_school') }})
    group by school_id, area, skill
)

select
    school_skills.*,
    benchmark.skill_description,
    benchmark.pct_correct                                       as benchmark_pct_correct,
    round(school_skills.pct_correct - benchmark.pct_correct, 1) as gap_vs_benchmark
from school_skills
join {{ ref('mart_school') }} as school using (school_id)
join {{ ref('mart_skill_gaps') }} as benchmark
    on  benchmark.state = school.state
    and benchmark.school_type = school.school_type
    and benchmark.area = school_skills.area
    and benchmark.skill = school_skills.skill
