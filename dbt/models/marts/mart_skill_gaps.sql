-- % of correct answers per skill, per state and school type, plus the whole country ("BR").
with by_group as (
    select
        coalesce(school_state, 'BR')                      as state,
        school_type,
        area,
        skill,
        count(*)                                          as answers,
        round(100 * avg(is_correct::int), 1)              as pct_correct
    from {{ ref('int_item_answers') }}
    group by grouping sets ((school_state, school_type, area, skill), (school_type, area, skill))
),

students as (
    select coalesce(school_state, 'BR') as state, school_type, count(*) as students
    from {{ ref('int_school_results') }}
    group by grouping sets ((school_state, school_type), (school_type))
)

select
    by_group.*,
    skills.description                                  as skill_description,
    students.students,
    rank() over (partition by by_group.state, by_group.school_type, by_group.area
                 order by by_group.pct_correct) as difficulty_rank
from by_group
join students using (state, school_type)
left join {{ ref('skills') }} as skills using (area, skill)
where students.students >= {{ var('min_group_size') }}
