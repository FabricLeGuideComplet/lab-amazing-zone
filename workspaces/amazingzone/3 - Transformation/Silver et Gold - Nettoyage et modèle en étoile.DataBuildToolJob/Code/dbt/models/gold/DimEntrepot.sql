-- Dimension entrepôt (SCD de type 1).
SELECT {{ cle_substitution(['code_entrepot']) }} AS EntrepotKey,
       CAST(code_entrepot AS VARCHAR(10))        AS CodeEntrepot,
       entrepot                                  AS Entrepot,
       ville                                     AS Ville,
       latitude                                  AS Latitude,
       longitude                                 AS Longitude,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))    AS DateChargement
FROM {{ ref('entrepot') }}
UNION ALL
SELECT -1, '?', 'Inconnu', 'Inconnue', NULL, NULL, CAST(SYSUTCDATETIME() AS DATETIME2(6))
