CREATE TABLE [gold].[DimTransporteur] (
    [TransporteurKey] BIGINT        NULL,
    [Transporteur]    VARCHAR (50)  NULL,
    [TypeLivraison]   VARCHAR (20)  NULL,
    [DateChargement]  DATETIME2 (6) NULL
);


GO