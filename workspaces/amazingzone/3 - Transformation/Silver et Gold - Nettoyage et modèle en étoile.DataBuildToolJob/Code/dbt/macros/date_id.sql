{# Clé de la dimension calendaire (AAAAMMJJ) à partir d'une date ou d'un horodatage. #}
{% macro date_id(colonne) -%}
    CONVERT(INT, CONVERT(VARCHAR(8), {{ colonne }}, 112))
{%- endmacro %}
