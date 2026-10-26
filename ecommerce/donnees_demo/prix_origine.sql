-- Prix d'origine des trois produits modifiés par changer_prix.sql : à rejouer avant le premier chargement
-- de la couche Gold pour reproduire la démonstration de l'historisation (snapshot dbt).
UPDATE dbo.Product SET Price = 1800.00, UpdatedOnUtc = SYSUTCDATETIME() WHERE Sku = 'AP_MBP_13';
UPDATE dbo.Product SET Price = 500.00,  UpdatedOnUtc = SYSUTCDATETIME() WHERE Sku = 'LE_IC_600';
UPDATE dbo.Product SET Price = 1500.00, UpdatedOnUtc = SYSUTCDATETIME() WHERE Sku = 'AS_551_LP';
