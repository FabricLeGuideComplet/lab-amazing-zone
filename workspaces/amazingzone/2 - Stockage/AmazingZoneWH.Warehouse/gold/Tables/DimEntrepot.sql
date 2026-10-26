CREATE TABLE [gold].[DimEntrepot] (
    [EntrepotKey]    BIGINT         NULL,
    [CodeEntrepot]   VARCHAR (10)   NULL,
    [Entrepot]       VARCHAR (8000) NULL,
    [Ville]          VARCHAR (8000) NULL,
    [Latitude]       FLOAT (53)     NULL,
    [Longitude]      FLOAT (53)     NULL,
    [DateChargement] DATETIME2 (6)  NULL
);


GO