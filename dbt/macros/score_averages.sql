{# avg_natural_sciences, avg_humanities, avg_languages, avg_math, avg_essay, avg_overall #}
{% macro score_averages() -%}
    {%- for column in score_columns() + ['score_overall'] %}
    round(avg({{ column }}), 1) as avg_{{ column[6:] }}{{ "," if not loop.last }}
    {%- endfor %}
{%- endmacro %}
