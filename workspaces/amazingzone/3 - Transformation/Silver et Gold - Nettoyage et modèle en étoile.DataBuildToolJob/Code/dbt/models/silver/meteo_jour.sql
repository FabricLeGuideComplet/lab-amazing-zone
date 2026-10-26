-- Météo quotidienne par entrepôt (valeurs consolidées des jours passés et prévisions des jours à venir),
-- avec l'indicateur d'intempérie validé avec la logistique : pluie forte, neige ou rafales violentes.
SELECT CAST(site AS VARCHAR(10))                AS code_entrepot,
       site_nom                                 AS entrepot,
       [date],
       temperature_2m_max                       AS temperature_max,
       temperature_2m_min                       AS temperature_min,
       precipitation_sum                        AS precipitations_mm,
       snowfall_sum                             AS neige_cm,
       wind_gusts_10m_max                       AS rafales_max_kmh,
       CAST(weather_code AS INT)                AS code_meteo,
       CAST(CASE WHEN precipitation_sum >= 10 OR snowfall_sum > 0 OR wind_gusts_10m_max >= 70
                 THEN 1 ELSE 0 END AS BIT)      AS est_jour_intemperie
FROM {{ source('meteo', 'weather_forecast') }}
