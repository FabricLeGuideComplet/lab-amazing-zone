-- Photo quotidienne du stock (periodic snapshot). Le WMS ne connaît que le stock courant : chaque exécution
-- ajoute (ou remplace) la photo du jour, et l'historique des jours précédents est conservé.
-- full_refresh: false protège la table d'un « dbt run --full-refresh » qui effacerait tout l'historique.
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='DateId',
        full_refresh=false,
    )
}}
SELECT {{ date_id('SYSUTCDATETIME()') }}            AS DateId,
       COALESCE(p.ProduitKey, -1)                   AS ProduitKey,
       COALESCE(e.EntrepotKey, -1)                  AS EntrepotKey,
       CAST(s.quantite_stock AS DECIMAL(18, 3))     AS QuantiteStock,
       CAST(s.quantite_reservee AS DECIMAL(18, 3))  AS QuantiteReservee,
       CAST(s.quantite_stock - s.quantite_reservee AS DECIMAL(18, 3)) AS QuantiteDisponible,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))       AS DateChargement
FROM {{ ref('stock') }} AS s
LEFT JOIN {{ ref('DimProduit') }} AS p ON p.Sku = s.sku AND p.EstVersionCourante = 1
LEFT JOIN {{ ref('DimEntrepot') }} AS e ON e.CodeEntrepot = s.code_entrepot
