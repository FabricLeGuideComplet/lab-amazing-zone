CREATE TABLE [gold].[DimDate] (
    [DateId]         INT          NULL,
    [Date]           DATE         NULL,
    [Annee]          SMALLINT     NULL,
    [NumTrimestre]   SMALLINT     NULL,
    [Trimestre]      VARCHAR (2)  NULL,
    [NumMois]        SMALLINT     NULL,
    [Mois]           VARCHAR (10) NULL,
    [AnneeMois]      INT          NULL,
    [MoisAnnee]      VARCHAR (16) NULL,
    [NumSemaineIso]  SMALLINT     NULL,
    [NumJourSemaine] SMALLINT     NULL,
    [JourSemaine]    VARCHAR (10) NULL,
    [EstWeekEnd]     BIT          NULL
);


GO