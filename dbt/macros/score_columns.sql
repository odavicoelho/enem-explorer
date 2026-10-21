{# The five ENEM scores, in the order INEP reports them. #}
{% macro score_columns() -%}
    {{ return(['score_natural_sciences', 'score_humanities', 'score_languages', 'score_math', 'score_essay']) }}
{%- endmacro %}
