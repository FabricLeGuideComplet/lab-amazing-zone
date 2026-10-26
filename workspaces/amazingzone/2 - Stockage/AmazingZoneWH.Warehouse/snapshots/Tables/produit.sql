CREATE TABLE [snapshots].[produit] (
    [produit_id]     INT             NULL,
    [sku]            VARCHAR (8000)  NULL,
    [produit]        VARCHAR (8000)  NULL,
    [univers]        VARCHAR (8000)  NULL,
    [categorie]      VARCHAR (8000)  NULL,
    [prix_vente]     DECIMAL (18, 2) NULL,
    [cout_achat]     DECIMAL (18, 2) NULL,
    [dbt_scd_id]     VARCHAR (32)    NULL,
    [dbt_updated_at] DATETIME2 (6)   NULL,
    [dbt_valid_from] DATETIME2 (6)   NULL,
    [dbt_valid_to]   DATETIME2 (6)   NULL
);


GO