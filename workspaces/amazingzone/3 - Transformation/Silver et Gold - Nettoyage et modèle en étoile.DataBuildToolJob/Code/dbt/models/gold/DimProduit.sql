-- Dimension produit (SCD de type 2) construite à partir du snapshot dbt du catalogue : une ligne par version.
-- La première version de chaque produit couvre tout son passé, pour que les ventes antérieures au premier
-- snapshot trouvent une version à laquelle se rattacher.
WITH versions AS (
    SELECT s.*,
           ROW_NUMBER() OVER (PARTITION BY s.produit_id ORDER BY s.dbt_valid_from) AS num_version
    FROM {{ ref('snapshot_produit') }} AS s
)
SELECT {{ cle_substitution(['produit_id', 'dbt_valid_from']) }} AS ProduitKey,
       produit_id                                     AS ProduitId,
       sku                                            AS Sku,
       produit                                        AS Produit,
       univers                                        AS Univers,
       categorie                                      AS Categorie,
       CAST(prix_vente AS DECIMAL(18, 2))             AS PrixVenteHT,
       CAST(cout_achat AS DECIMAL(18, 2))             AS CoutAchat,
       CAST(CASE WHEN num_version = 1 THEN '1900-01-01' ELSE dbt_valid_from END AS DATETIME2(6)) AS DateDebutValidite,
       CAST(dbt_valid_to AS DATETIME2(6))             AS DateFinValidite,
       CAST(CASE WHEN dbt_valid_to IS NULL THEN 1 ELSE 0 END AS BIT) AS EstVersionCourante,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))         AS DateChargement
FROM versions
UNION ALL
SELECT -1, -1, NULL, 'Inconnu', 'Inconnu', 'Inconnue', NULL, NULL,
       CAST('1900-01-01' AS DATETIME2(6)), NULL, CAST(1 AS BIT), CAST(SYSUTCDATETIME() AS DATETIME2(6))
