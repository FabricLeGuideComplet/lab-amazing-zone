-- Fraîcheur du Bronze : les prévisions sont rechargées chaque matin. Si la dernière extraction visible par le
-- point de terminaison SQL date de plus de 26 heures (ingestion en échec, synchronisation non faite), le test
-- échoue et les modèles qui dépendent de la météo ne sont pas reconstruits sur des données de l'avant-veille.
-- Le job dbt de Fabric ne proposant pas la commande « source freshness », la règle est portée par ce test.
SELECT MAX(date_extraction_utc) AS derniere_extraction_utc
FROM {{ source('meteo', 'weather_forecast_issued') }}
HAVING MAX(date_extraction_utc) < DATEADD(HOUR, -26, SYSUTCDATETIME())
