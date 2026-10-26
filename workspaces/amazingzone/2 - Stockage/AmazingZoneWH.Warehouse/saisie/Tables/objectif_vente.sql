CREATE TABLE [saisie].[objectif_vente] (
    [Mois]       DATE            NOT NULL,
    [Univers]    VARCHAR (50)    NOT NULL,
    [ObjectifHT] DECIMAL (18, 2) NOT NULL,
    [SaisiPar]   VARCHAR (256)   NOT NULL,
    [SaisiLe]    DATETIME2 (0)   NOT NULL
);


GO