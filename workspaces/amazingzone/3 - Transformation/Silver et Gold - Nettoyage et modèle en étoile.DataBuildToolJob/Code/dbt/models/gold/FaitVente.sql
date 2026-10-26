-- Ventes, à la maille de la ligne de commande (commandes annulées exclues), reconstruites à chaque exécution :
-- au volume d'Amazing Zone, plus simple et plus robuste qu'un chargement incrémental.
SELECT {{ date_id('l.date_commande') }}       AS DateCommandeId,
       COALESCE(c.ClientKey, -1)               AS ClientKey,
       COALESCE(p.ProduitKey, -1)              AS ProduitKey,
       COALESCE(e.EntrepotKey, -1)             AS EntrepotKey,
       CAST(l.numero_commande AS VARCHAR(20))  AS NumeroCommande,
       CAST(l.statut_commande AS VARCHAR(20))  AS StatutCommande,
       CAST(l.mode_livraison AS VARCHAR(50))   AS ModeLivraison,
       l.quantite                              AS Quantite,
       l.prix_unitaire_ht                      AS PrixUnitaireHT,
       l.montant_ht                            AS MontantHT,
       l.cout_achat                            AS CoutAchat,
       CAST(l.montant_ht - l.cout_achat AS DECIMAL(18, 2)) AS MargeHT,
       CAST(SYSUTCDATETIME() AS DATETIME2(6))  AS DateChargement
FROM {{ ref('commande_ligne') }} AS l
LEFT JOIN {{ ref('DimClient') }} AS c ON c.ClientId = l.client_id
-- version du produit valide à la date de la commande
LEFT JOIN {{ ref('DimProduit') }} AS p
       ON p.ProduitId = l.produit_id
      AND l.date_commande >= p.DateDebutValidite
      AND l.date_commande < COALESCE(p.DateFinValidite, '9999-12-31')
LEFT JOIN {{ ref('commande_logistique') }} AS w ON w.numero_commande = l.numero_commande
LEFT JOIN {{ ref('DimEntrepot') }} AS e ON e.CodeEntrepot = w.code_entrepot
WHERE l.statut_commande <> 'Annulée'
