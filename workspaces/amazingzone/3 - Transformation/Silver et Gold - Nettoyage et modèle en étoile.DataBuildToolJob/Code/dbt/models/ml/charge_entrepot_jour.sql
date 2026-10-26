-- Table de caractéristiques (One Big Table) pour prévoir la charge des entrepôts : une ligne par entrepôt et
-- par jour. Cible : nombre de commandes prises en charge par l'entrepôt ce jour-là. Réservée au Machine Learning,
-- elle ne doit pas servir de modèle d'analyse.
-- Chaque ligne ne contient que ce qui est connu la veille au matin, au moment où la logistique planifie :
-- la prévision météo émise la veille (et non la météo observée), et un historique des ventes arrêté à J-2.
WITH grille AS (
    SELECT e.code_entrepot, d.[Date] AS jour, d.NumJourSemaine, d.NumMois, d.EstWeekEnd
    FROM {{ ref('entrepot') }} AS e
    CROSS JOIN {{ ref('DimDate') }} AS d
    WHERE d.[Date] >= '2025-01-01'
      AND d.[Date] <= (SELECT MAX([date]) FROM {{ source('meteo', 'weather_forecast_issued') }} WHERE echeance_jours = 1)
),
charge AS (
    SELECT code_entrepot,
           CAST(date_prise_en_charge AT TIME ZONE 'UTC' AT TIME ZONE 'Romance Standard Time' AS DATE) AS jour,
           COUNT(*)         AS nb_commandes,
           SUM(nb_articles) AS nb_articles
    FROM {{ ref('commande_logistique') }}
    WHERE code_entrepot IS NOT NULL
    GROUP BY code_entrepot,
             CAST(date_prise_en_charge AT TIME ZONE 'UTC' AT TIME ZONE 'Romance Standard Time' AS DATE)
),
dernier_jour AS (SELECT MAX(jour) AS jour FROM charge),
historique AS (
    -- zéro pour un jour passé sans commande, vide pour les jours à prévoir
    SELECT g.*,
           CASE WHEN g.jour <= dj.jour THEN COALESCE(c.nb_commandes, 0) END AS nb_commandes,
           CASE WHEN g.jour <= dj.jour THEN COALESCE(c.nb_articles, 0) END  AS nb_articles,
           CAST(CASE WHEN g.jour > dj.jour THEN 1 ELSE 0 END AS BIT)        AS est_a_prevoir
    FROM grille AS g
    CROSS JOIN dernier_jour AS dj
    LEFT JOIN charge AS c ON c.code_entrepot = g.code_entrepot AND c.jour = g.jour
)
SELECT h.code_entrepot,
       h.jour,
       h.nb_commandes,                                         -- cible
       h.nb_articles,
       h.est_a_prevoir,
       -- calendrier
       h.NumJourSemaine                                        AS jour_semaine,
       h.NumMois                                               AS mois,
       CAST(h.EstWeekEnd AS INT)                               AS est_week_end,
       CASE WHEN h.NumMois = 12 AND DAY(h.jour) <= 24 THEN 1 ELSE 0 END AS est_periode_noel,
       -- prévision météo émise la veille (échéance 1 jour) ; les rafales ne sont archivées que depuis août 2026
       p.temperature_2m_max                                    AS temperature_max_prevue,
       p.temperature_2m_min                                    AS temperature_min_prevue,
       p.precipitation_sum                                     AS precipitations_prevues_mm,
       p.snowfall_sum                                          AS neige_prevue_cm,
       p.wind_gusts_10m_max                                    AS rafales_prevues_kmh,
       CASE WHEN p.precipitation_sum >= 10 OR p.snowfall_sum > 0 OR p.wind_gusts_10m_max >= 70
            THEN 1 ELSE 0 END                                  AS est_intemperie_prevue,
       -- historique de la charge, connu la veille au matin : rien après J-2
       LAG(h.nb_commandes, 7) OVER (PARTITION BY h.code_entrepot ORDER BY h.jour) AS nb_commandes_j_moins_7,
       AVG(CAST(h.nb_commandes AS FLOAT)) OVER (PARTITION BY h.code_entrepot ORDER BY h.jour
                                                ROWS BETWEEN 29 PRECEDING AND 2 PRECEDING) AS moyenne_commandes_28j
FROM historique AS h
LEFT JOIN {{ source('meteo', 'weather_forecast_issued') }} AS p
       ON p.site = h.code_entrepot AND p.[date] = h.jour AND p.echeance_jours = 1
