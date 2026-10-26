-- Météo quotidienne par entrepôt : observations passées et prévisions des jours à venir.
SELECT {{ date_id('m.[date]') }}                    AS DateId,
       COALESCE(e.EntrepotKey, -1)                  AS EntrepotKey,
       m.temperature_max                            AS TemperatureMax,
       m.temperature_min                            AS TemperatureMin,
       m.precipitations_mm                          AS PrecipitationsMm,
       m.neige_cm                                   AS NeigeCm,
       m.rafales_max_kmh                            AS RafalesMaxKmh,
       CAST(m.est_jour_intemperie AS BIT)           AS EstJourIntemperie,
       CAST(CASE WHEN m.[date] > CAST(SYSUTCDATETIME() AS DATE) THEN 1 ELSE 0 END AS BIT) AS EstPrevision,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))       AS DateChargement
FROM {{ ref('meteo_jour') }} AS m
LEFT JOIN {{ ref('DimEntrepot') }} AS e ON e.CodeEntrepot = m.code_entrepot
