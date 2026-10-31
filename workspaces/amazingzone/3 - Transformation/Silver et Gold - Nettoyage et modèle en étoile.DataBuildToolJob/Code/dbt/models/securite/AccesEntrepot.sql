-- Correspondance entre utilisateurs et entrepôts, lue par la sécurité au niveau des lignes du Warehouse
-- (fonction securite.fn_acces_entrepot) et par le rôle dynamique du modèle « Ventes et logistique ».
-- Un responsable d'entrepôt a une ligne, la direction une ligne par entrepôt.
SELECT CAST(s.utilisateur AS VARCHAR(256)) AS Utilisateur,
       e.EntrepotKey,
       e.CodeEntrepot
FROM {{ ref('securite_entrepot') }} AS s
JOIN {{ ref('DimEntrepot') }} AS e
  ON e.CodeEntrepot = s.code_entrepot
