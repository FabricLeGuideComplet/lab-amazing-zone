CREATE TABLE [gold].[DimClient] (
    [ClientKey]       BIGINT         NULL,
    [ClientId]        INT            NOT NULL,
    [Email]           VARCHAR (8000) NULL,
    [Prenom]          VARCHAR (8000) NULL,
    [Nom]             VARCHAR (8000) NULL,
    [NomComplet]      VARCHAR (8000) NOT NULL,
    [Genre]           VARCHAR (5)    NULL,
    [CodePostal]      VARCHAR (8000) NULL,
    [Ville]           VARCHAR (8000) NULL,
    [CodeDepartement] VARCHAR (24)   NULL,
    [Departement]     VARCHAR (8000) NULL,
    [Region]          VARCHAR (8000) NULL,
    [DateInscription] DATE           NULL,
    [DateChargement]  DATETIME2 (6)  NULL
);


GO