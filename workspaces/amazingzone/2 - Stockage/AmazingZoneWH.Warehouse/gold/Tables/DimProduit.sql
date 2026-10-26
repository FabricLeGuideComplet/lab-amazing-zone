CREATE TABLE [gold].[DimProduit] (
    [ProduitKey]         BIGINT          NULL,
    [ProduitId]          INT             NULL,
    [Sku]                VARCHAR (8000)  NULL,
    [Produit]            VARCHAR (8000)  NULL,
    [Univers]            VARCHAR (8000)  NULL,
    [Categorie]          VARCHAR (8000)  NULL,
    [PrixVenteHT]        DECIMAL (18, 2) NULL,
    [CoutAchat]          DECIMAL (18, 2) NULL,
    [DateDebutValidite]  DATETIME2 (6)   NULL,
    [DateFinValidite]    DATETIME2 (6)   NULL,
    [EstVersionCourante] BIT             NULL,
    [DateChargement]     DATETIME2 (6)   NULL
);


GO