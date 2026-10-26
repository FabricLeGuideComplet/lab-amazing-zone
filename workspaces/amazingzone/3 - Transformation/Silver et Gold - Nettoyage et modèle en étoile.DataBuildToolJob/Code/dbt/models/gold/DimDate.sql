-- Dimension calendaire : une ligne par jour du 1er janvier 2025 au 31 décembre 2027.
WITH chiffres AS (
    SELECT n FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS v(n)
),
jours AS (
    SELECT DATEADD(DAY, a.n + 10 * b.n + 100 * c.n + 1000 * d.n, CAST('2025-01-01' AS DATE)) AS [Date]
    FROM chiffres a CROSS JOIN chiffres b CROSS JOIN chiffres c CROSS JOIN chiffres d
    WHERE a.n + 10 * b.n + 100 * c.n + 1000 * d.n <= DATEDIFF(DAY, '2025-01-01', '2027-12-31')
),
calcul AS (
    SELECT [Date],
           DATEPART(YEAR, [Date])    AS Annee,
           DATEPART(QUARTER, [Date]) AS NumTrimestre,
           DATEPART(MONTH, [Date])   AS NumMois,
           (DATEDIFF(DAY, '19000101', [Date]) % 7) + 1 AS NumJourSemaine   -- 1 = lundi
    FROM jours
)
SELECT {{ date_id('[Date]') }}                         AS DateId,
       [Date],
       CAST(Annee AS SMALLINT)                         AS Annee,
       CAST(NumTrimestre AS SMALLINT)                  AS NumTrimestre,
       CAST(CONCAT('T', NumTrimestre) AS VARCHAR(2))   AS Trimestre,
       CAST(NumMois AS SMALLINT)                       AS NumMois,
       CAST(CASE NumMois WHEN 1 THEN 'janvier' WHEN 2 THEN 'février' WHEN 3 THEN 'mars' WHEN 4 THEN 'avril'
                         WHEN 5 THEN 'mai' WHEN 6 THEN 'juin' WHEN 7 THEN 'juillet' WHEN 8 THEN 'août'
                         WHEN 9 THEN 'septembre' WHEN 10 THEN 'octobre' WHEN 11 THEN 'novembre'
                         ELSE 'décembre' END AS VARCHAR(10)) AS Mois,
       Annee * 100 + NumMois                           AS AnneeMois,
       CAST(CONCAT(CASE NumMois WHEN 1 THEN 'janv.' WHEN 2 THEN 'févr.' WHEN 3 THEN 'mars' WHEN 4 THEN 'avr.'
                                WHEN 5 THEN 'mai' WHEN 6 THEN 'juin' WHEN 7 THEN 'juil.' WHEN 8 THEN 'août'
                                WHEN 9 THEN 'sept.' WHEN 10 THEN 'oct.' WHEN 11 THEN 'nov.' ELSE 'déc.' END,
                   ' ', Annee) AS VARCHAR(16))        AS MoisAnnee,
       CAST(DATEPART(ISO_WEEK, [Date]) AS SMALLINT)    AS NumSemaineIso,
       CAST(NumJourSemaine AS SMALLINT)                AS NumJourSemaine,
       CAST(CASE NumJourSemaine WHEN 1 THEN 'lundi' WHEN 2 THEN 'mardi' WHEN 3 THEN 'mercredi' WHEN 4 THEN 'jeudi'
                                WHEN 5 THEN 'vendredi' WHEN 6 THEN 'samedi' ELSE 'dimanche' END AS VARCHAR(10)) AS JourSemaine,
       CAST(CASE WHEN NumJourSemaine IN (6, 7) THEN 1 ELSE 0 END AS BIT) AS EstWeekEnd
FROM calcul
