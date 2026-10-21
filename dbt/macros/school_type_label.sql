{% macro school_type_label(code) -%}
    case {{ code }}
        when 1 then 'Federal'
        when 2 then 'Estadual'
        when 3 then 'Municipal'
        when 4 then 'Privada'
    end
{%- endmacro %}
