-- Clients du site e-commerce, géographie rapprochée du référentiel par le département déduit du code postal.
WITH clients AS (
    SELECT c.Id                                        AS client_id,
           LOWER(TRIM(c.Email))                        AS email,
           c.FirstName                                 AS prenom,
           c.LastName                                  AS nom,
           CASE c.Gender WHEN 'M' THEN 'Homme' WHEN 'F' THEN 'Femme' END AS genre,
           c.ZipPostalCode                             AS code_postal,
           c.City                                      AS ville,
           -- département déduit du code postal : Corse (2A/2B) et outre-mer (3 chiffres) compris
           CASE WHEN c.ZipPostalCode LIKE '97%' THEN SUBSTRING(c.ZipPostalCode, 1, 3)
                WHEN c.ZipPostalCode LIKE '20%' THEN CASE WHEN c.ZipPostalCode < '20200' THEN '2A' ELSE '2B' END
                ELSE SUBSTRING(c.ZipPostalCode, 1, 2)
           END                                         AS code_departement,
           CAST(c.CreatedOnUtc AS DATE)                AS date_inscription
    FROM {{ source('ecommerce', 'Customer') }} AS c
    WHERE c.Deleted = 0 AND c.IsSystemAccount = 0 AND c.Email LIKE '%_@_%'
)
SELECT c.client_id, c.email, c.prenom, c.nom, c.genre, c.code_postal, c.ville,
       c.code_departement, g.departement, g.region, c.date_inscription
FROM clients AS c
LEFT JOIN {{ source('referentiels', 'geographie') }} AS g ON g.code_departement = c.code_departement
