-- Federal / state / municipal / private, per state and for the whole country ("BR").
select
    coalesce(school_state, 'BR')    as state,
    school_type,
    count(distinct school_id)       as schools,
    count(*)                        as students,
    {{ score_averages() }}
from {{ ref('int_school_results') }}
group by grouping sets ((school_state, school_type), (school_type))
having count(*) >= {{ var('min_group_size') }}
