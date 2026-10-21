select
    school_state                as state,
    count(distinct school_id)   as schools,
    count(*)                    as students,
    {{ score_averages() }}
from {{ ref('int_school_results') }}
group by school_state
having count(*) >= {{ var('min_group_size') }}
