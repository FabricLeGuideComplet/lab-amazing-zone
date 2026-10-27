-- Stock disponible par article et par entrepôt, exposé au site e-commerce par l'API pour GraphQL
-- « API_Stock_disponible ». Une table dédiée plutôt que silver.stock : seules les colonnes utiles au site
-- sont exposées, et la clé primaire exigée par l'API est déclarée après chaque reconstruction (post_hook).
-- Les ISNULL rendent les colonnes de la clé non nullables, condition pour déclarer la contrainte.
{{ config(
    post_hook="ALTER TABLE {{ this }} ADD CONSTRAINT pk_stock_disponible PRIMARY KEY NONCLUSTERED (sku, code_entrepot) NOT ENFORCED"
) }}
SELECT ISNULL(s.sku, '')                                        AS sku,
       ISNULL(s.code_entrepot, '')                              AS code_entrepot,
       CAST(s.quantite_stock - s.quantite_reservee AS INT)      AS quantite_disponible,
       s.date_maj                                               AS date_maj_wms
FROM {{ ref('stock') }} AS s
