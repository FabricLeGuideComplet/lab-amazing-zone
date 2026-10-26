CREATE TABLE [gold].[FaitVente] (
    [DateCommandeId] INT             NULL,
    [ClientKey]      BIGINT          NULL,
    [ProduitKey]     BIGINT          NULL,
    [EntrepotKey]    BIGINT          NULL,
    [NumeroCommande] VARCHAR (20)    NULL,
    [StatutCommande] VARCHAR (20)    NULL,
    [ModeLivraison]  VARCHAR (50)    NULL,
    [Quantite]       INT             NOT NULL,
    [PrixUnitaireHT] DECIMAL (18, 2) NULL,
    [MontantHT]      DECIMAL (18, 2) NULL,
    [CoutAchat]      DECIMAL (18, 2) NULL,
    [MargeHT]        DECIMAL (18, 2) NULL,
    [DateChargement] DATETIME2 (6)   NULL
);


GO