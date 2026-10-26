CREATE TABLE [gold].[FaitExpedition] (
    [NumeroCommande]         VARCHAR (20)   NULL,
    [DatePriseEnChargeId]    INT            NULL,
    [DateExpeditionId]       INT            NULL,
    [EntrepotKey]            BIGINT         NULL,
    [TransporteurKey]        BIGINT         NULL,
    [ClientKey]              BIGINT         NULL,
    [StatutLogistique]       VARCHAR (20)   NULL,
    [NbLignes]               INT            NULL,
    [NbArticles]             INT            NULL,
    [DelaiPreparationHeures] DECIMAL (9, 2) NULL,
    [EstExpedieeSous24h]     BIT            NULL,
    [DateChargement]         DATETIME2 (6)  NULL
);


GO