-- Stock courant du WMS par article et par entrepôt (le WMS ne conserve que l'état courant).
SELECT CAST(i.sku AS VARCHAR(50))   AS sku,
       CAST(w.code AS VARCHAR(10))  AS code_entrepot,
       SUM(inv.qty_on_hand)         AS quantite_stock,
       SUM(inv.qty_reserved)        AS quantite_reservee,
       MAX(inv.date_maj)            AS date_maj
FROM {{ source('wms', 'inventory') }} AS inv
INNER JOIN {{ source('wms', 'item') }} AS i      ON i.item_id = inv.item_id
INNER JOIN {{ source('wms', 'location') }} AS l  ON l.location_id = inv.location_id
INNER JOIN {{ source('wms', 'warehouse') }} AS w ON w.warehouse_id = l.warehouse_id
WHERE inv.qty_on_hand >= 0
GROUP BY i.sku, w.code
