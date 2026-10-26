{# Clé de substitution déterministe (BIGINT) calculée par hachage des colonnes de la clé métier.
   Contrairement à une colonne IDENTITY, elle reste identique d'une reconstruction à l'autre de la table,
   ce qui permet à dbt de recréer les dimensions sans rompre les liens avec les faits.
   Pour une clé composée, CONCAT_WS ignorerait les valeurs NULL : chaque colonne vide est remplacée par un
   marqueur, pour que (1, NULL, 2) et (1, 2, NULL) ne donnent pas la même clé. Le hachage est tronqué à 64 bits
   (BIGINT) : les collisions sont improbables à cette échelle, pas impossibles. #}
{% macro cle_substitution(colonnes) -%}
    {%- if colonnes | length == 1 -%}
    CAST(HASHBYTES('SHA2_256', CAST({{ colonnes[0] }} AS VARCHAR(200))) AS BIGINT)
    {%- else -%}
    CAST(HASHBYTES('SHA2_256', CONCAT_WS('|',
        {%- for c in colonnes %} COALESCE(CAST({{ c }} AS VARCHAR(200)), '<NULL>')
        {%- if not loop.last %},{% endif %}{% endfor %})) AS BIGINT)
    {%- endif -%}
{%- endmacro %}
