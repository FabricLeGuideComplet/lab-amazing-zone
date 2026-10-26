-- Taux de change annuels contre l'euro, une ligne par devise et par année. Le fichier Excel donne un taux par
-- pays : les pays qui partagent une devise (l'euro, le dollar…) répètent donc le même taux, que QUALIFY
-- ne garde qu'une fois, sans sous-requête.
SELECT CAST([Code devise] AS VARCHAR(3))     AS code_devise,
       CAST(Annee AS SMALLINT)               AS annee,
       CAST(TauxChange AS DECIMAL(18, 6))    AS taux_change
FROM {{ source('referentiels', 'taux_change') }}
WHERE TauxChange IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY [Code devise], Annee ORDER BY [Code ISO-3]) = 1
