-- Dimension transporteur, à partir des transporteurs rencontrés dans les expéditions.
SELECT {{ cle_substitution(['transporteur']) }}  AS TransporteurKey,
       CAST(transporteur AS VARCHAR(50))         AS Transporteur,
       CAST(CASE transporteur WHEN 'Chronopost' THEN 'Express' WHEN 'Retrait' THEN 'Retrait'
                              ELSE 'Standard' END AS VARCHAR(20)) AS TypeLivraison,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))    AS DateChargement
FROM (SELECT DISTINCT transporteur FROM {{ ref('commande_logistique') }} WHERE transporteur IS NOT NULL) AS t
UNION ALL
SELECT -1, 'Non expédiée', 'Non expédiée', CAST(SYSUTCDATETIME() AS DATETIME2(6))
