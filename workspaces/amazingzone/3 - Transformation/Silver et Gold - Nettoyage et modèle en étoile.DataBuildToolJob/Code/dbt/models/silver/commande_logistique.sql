-- Commandes logistiques du WMS : entrepôt de préparation, statut, expédition (une ligne par commande).
WITH lignes AS (
    SELECT order_id, COUNT(*) AS nb_lignes, SUM(qty_ordered) AS nb_articles
    FROM {{ source('wms', 'order_line') }}
    GROUP BY order_id
),
expeditions AS (
    SELECT order_id, MIN(shipped_at) AS date_expedition, MAX(carrier) AS transporteur,
           MAX(tracking_no) AS numero_suivi
    FROM {{ source('wms', 'shipment') }}
    GROUP BY order_id
)
SELECT o.order_id                                   AS commande_wms_id,
       CAST(o.order_no AS VARCHAR(20))              AS numero_commande,
       CAST(w.code AS VARCHAR(10))                  AS code_entrepot,
       CAST(CASE o.status
                WHEN 'CREATED'   THEN 'Créée'
                WHEN 'ALLOCATED' THEN 'Allouée'
                WHEN 'PICKED'    THEN 'Prélevée'
                WHEN 'PACKED'    THEN 'Emballée'
                WHEN 'SHIPPED'   THEN 'Expédiée'
                WHEN 'CANCELLED' THEN 'Annulée'
                ELSE o.status
            END AS VARCHAR(20))                     AS statut_logistique,
       o.order_date                                 AS date_prise_en_charge,
       e.date_expedition,
       CAST(e.transporteur AS VARCHAR(50))          AS transporteur,
       e.numero_suivi,
       CAST(l.nb_lignes AS INT)                     AS nb_lignes,
       CAST(l.nb_articles AS INT)                   AS nb_articles
FROM {{ source('wms', 'orders') }} AS o
LEFT JOIN {{ source('wms', 'warehouse') }} AS w ON w.warehouse_id = o.warehouse_id
LEFT JOIN lignes AS l      ON l.order_id = o.order_id
LEFT JOIN expeditions AS e ON e.order_id = o.order_id
WHERE o.order_no IS NOT NULL
