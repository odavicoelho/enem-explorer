-- Staging must never drop or duplicate rows from the source.
select 'results' as source_name
where (select count(*) from {{ ref('stg_results') }}) != (select count(*) from {{ source('inep', 'results') }})
union all
select 'items'
where (select count(*) from {{ ref('stg_items') }}) != (select count(*) from {{ source('inep', 'items') }})
