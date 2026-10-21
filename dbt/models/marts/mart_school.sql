-- One row per school with enough students to publish (see var min_group_size).
with schools as (
    select
        school_id,
        any_value(school_city_id)   as city_id,
        any_value(school_city)      as city,
        any_value(school_state)     as state,
        any_value(school_type)      as school_type,
        any_value(school_location)  as school_location,
        count(*)                    as students,
        {{ score_averages() }}
    from {{ ref('int_school_results') }}
    group by school_id
    having count(*) >= {{ var('min_group_size') }}
)

select
    *,
    rank() over (partition by state order by avg_overall desc)               as rank_in_state,
    count(*) over (partition by state)                                       as schools_in_state,
    rank() over (partition by state, school_type order by avg_overall desc)  as rank_in_state_and_type,
    count(*) over (partition by state, school_type)                          as schools_in_state_and_type,
    round(100 * percent_rank() over (order by avg_overall), 1)               as national_percentile
from schools
