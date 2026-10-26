CREATE TABLE [silver].[produit] (
    [produit_id] INT             NOT NULL,
    [sku]        VARCHAR (50)    NULL,
    [produit]    VARCHAR (8000)  NOT NULL,
    [univers]    VARCHAR (8000)  NULL,
    [categorie]  VARCHAR (8000)  NULL,
    [prix_vente] DECIMAL (18, 2) NULL,
    [cout_achat] DECIMAL (18, 2) NULL,
    [publie]     BIT             NOT NULL
);


GO