-- Entrepôts d'Amazing Zone (WMS), avec la ville extraite du libellé et les coordonnées du référentiel des sites.
SELECT CAST(w.code AS VARCHAR(10))                       AS code_entrepot,
       w.name                                            AS entrepot,
       CASE WHEN CHARINDEX('(', w.name) > 0 AND CHARINDEX(')', w.name) > CHARINDEX('(', w.name)
            THEN SUBSTRING(w.name, CHARINDEX('(', w.name) + 1, CHARINDEX(')', w.name) - CHARINDEX('(', w.name) - 1)
       END                                               AS ville,
       c.latitude,
       c.longitude
FROM {{ source('wms', 'warehouse') }} AS w
LEFT JOIN {{ ref('coordonnees_entrepots') }} AS c ON c.code_entrepot = w.code
