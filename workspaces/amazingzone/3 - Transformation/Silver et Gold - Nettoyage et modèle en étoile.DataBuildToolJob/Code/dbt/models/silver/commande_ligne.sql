-- Lignes de commande du site e-commerce, avec les statuts de la commande en clair.
SELECT oi.Id                                               AS ligne_id,
       o.Id                                                AS commande_id,
       CAST(o.CustomOrderNumber AS VARCHAR(20))            AS numero_commande,
       o.CustomerId                                        AS client_id,
       oi.ProductId                                        AS produit_id,
       o.CreatedOnUtc                                      AS date_commande,
       o.PaidDateUtc                                       AS date_paiement,
       CAST(CASE o.OrderStatusId WHEN 10 THEN 'En attente' WHEN 20 THEN 'En cours'
                                 WHEN 30 THEN 'Terminée'   WHEN 40 THEN 'Annulée' END AS VARCHAR(20)) AS statut_commande,
       CAST(CASE o.PaymentStatusId WHEN 10 THEN 'En attente' WHEN 20 THEN 'Autorisé' WHEN 30 THEN 'Payé'
                                   WHEN 35 THEN 'Remboursé partiellement' WHEN 40 THEN 'Remboursé'
                                   WHEN 50 THEN 'Annulé' END AS VARCHAR(30))                 AS statut_paiement,
       CAST(CASE o.ShippingStatusId WHEN 10 THEN 'Sans livraison' WHEN 20 THEN 'Non expédiée'
                                    WHEN 25 THEN 'Partiellement expédiée' WHEN 30 THEN 'Expédiée'
                                    WHEN 40 THEN 'Livrée' END AS VARCHAR(30))                AS statut_livraison,
       CAST(CASE o.ShippingMethod WHEN 'Ground' THEN 'Standard' WHEN 'Next Day Air' THEN 'Express'
                                  WHEN 'Pickup in store' THEN 'Retrait' ELSE o.ShippingMethod END AS VARCHAR(50)) AS mode_livraison,
       oi.Quantity                                         AS quantite,
       CAST(oi.UnitPriceExclTax AS DECIMAL(18, 2))         AS prix_unitaire_ht,
       CAST(oi.PriceExclTax AS DECIMAL(18, 2))             AS montant_ht,
       CAST(oi.OriginalProductCost * oi.Quantity AS DECIMAL(18, 2)) AS cout_achat
FROM {{ source('ecommerce', 'OrderItem') }} AS oi
INNER JOIN {{ source('ecommerce', 'Order') }} AS o ON o.Id = oi.OrderId
WHERE o.Deleted = 0 AND oi.Quantity > 0
