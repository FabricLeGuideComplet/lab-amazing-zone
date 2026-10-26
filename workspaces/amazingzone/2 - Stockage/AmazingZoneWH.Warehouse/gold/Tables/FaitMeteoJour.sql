CREATE TABLE [gold].[FaitMeteoJour] (
    [DateId]            INT           NULL,
    [EntrepotKey]       BIGINT        NULL,
    [TemperatureMax]    FLOAT (53)    NULL,
    [TemperatureMin]    FLOAT (53)    NULL,
    [PrecipitationsMm]  FLOAT (53)    NULL,
    [NeigeCm]           FLOAT (53)    NULL,
    [RafalesMaxKmh]     FLOAT (53)    NULL,
    [EstJourIntemperie] BIT           NULL,
    [EstPrevision]      BIT           NULL,
    [DateChargement]    DATETIME2 (6) NULL
);


GO