CREATE TABLE [gold].[FaitStockJour] (
    [DateId]             INT             NULL,
    [ProduitKey]         BIGINT          NULL,
    [EntrepotKey]        BIGINT          NULL,
    [QuantiteStock]      DECIMAL (18, 3) NULL,
    [QuantiteReservee]   DECIMAL (18, 3) NULL,
    [QuantiteDisponible] DECIMAL (18, 3) NULL,
    [DateChargement]     DATETIME2 (6)   NULL
);


GO