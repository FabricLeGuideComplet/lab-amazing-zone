-- Évolution du catalogue pour illustrer l'historisation (SCD de type 2) de la dimension produit :
-- baisse de prix sur deux produits, hausse sur un troisième. À exécuter après un premier chargement
-- de la couche Gold (snapshot dbt initial), puis relancer l'orchestration des transformations.
UPDATE dbo.Product SET Price = 1690.00, UpdatedOnUtc = SYSUTCDATETIME() WHERE Sku = 'AP_MBP_13';
UPDATE dbo.Product SET Price = 449.00,  UpdatedOnUtc = SYSUTCDATETIME() WHERE Sku = 'LE_IC_600';
UPDATE dbo.Product SET Price = 1590.00, UpdatedOnUtc = SYSUTCDATETIME() WHERE Sku = 'AS_551_LP';
