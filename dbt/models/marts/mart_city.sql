-- One row per city, by where the schools are (not where the exam was taken).
with cities as (
    select
        school_city_id              as city_id,
        any_value(school_city)      as city,
        any_value(school_state)     as state,
        count(distinct school_id)   as schools,
        count(*)                    as students,
        {{ score_averages() }}
    from {{ ref('int_school_results') }}
    group by school_city_id
    having count(*) >= {{ var('min_group_size') }}
)

select
    *,
    rank() over (partition by state order by avg_overall desc) as rank_in_state,
    count(*) over (partition by state)                         as cities_in_state
from cities
