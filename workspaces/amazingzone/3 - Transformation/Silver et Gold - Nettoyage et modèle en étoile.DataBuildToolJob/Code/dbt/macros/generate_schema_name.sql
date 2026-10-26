{# Les schémas portent exactement le nom de la couche (gold, snapshots) : sans cette macro, dbt les
   préfixerait par le schéma de la cible (par exemple dbo_gold). #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
