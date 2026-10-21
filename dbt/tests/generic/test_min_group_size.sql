{# Privacy guard (LGPD): fails if any published group has fewer students than var('min_group_size'). #}
{% test min_group_size(model, column_name) %}
select * from {{ model }} where {{ column_name }} < {{ var('min_group_size') }}
{% endtest %}
