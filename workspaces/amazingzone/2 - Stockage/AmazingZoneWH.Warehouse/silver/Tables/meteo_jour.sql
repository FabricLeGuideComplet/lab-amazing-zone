CREATE TABLE [silver].[meteo_jour] (
    [code_entrepot]       VARCHAR (10)   NULL,
    [entrepot]            VARCHAR (8000) NULL,
    [date]                DATE           NULL,
    [temperature_max]     FLOAT (53)     NULL,
    [temperature_min]     FLOAT (53)     NULL,
    [precipitations_mm]   FLOAT (53)     NULL,
    [neige_cm]            FLOAT (53)     NULL,
    [rafales_max_kmh]     FLOAT (53)     NULL,
    [code_meteo]          INT            NULL,
    [est_jour_intemperie] BIT            NULL
);


GO