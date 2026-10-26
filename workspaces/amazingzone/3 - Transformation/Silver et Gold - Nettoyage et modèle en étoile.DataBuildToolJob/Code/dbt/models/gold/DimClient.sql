-- Dimension client (SCD de type 1 : reconstruite à chaque exécution avec la dernière valeur des attributs).
SELECT {{ cle_substitution(['client_id']) }}   AS ClientKey,
       client_id                               AS ClientId,
       email                                   AS Email,
       prenom                                  AS Prenom,
       nom                                     AS Nom,
       CONCAT(prenom, ' ', nom)                AS NomComplet,
       genre                                   AS Genre,
       code_postal                             AS CodePostal,
       ville                                   AS Ville,
       code_departement                        AS CodeDepartement,
       departement                             AS Departement,
       region                                  AS Region,
       date_inscription                        AS DateInscription,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))  AS DateChargement
FROM {{ ref('client') }}
UNION ALL
-- membre « Inconnu », pour les faits dont le client n'est pas (encore) connu
SELECT -1, -1, NULL, NULL, NULL, 'Inconnu', NULL, NULL, 'Inconnue', NULL, 'Inconnu', 'Inconnue', NULL,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))
