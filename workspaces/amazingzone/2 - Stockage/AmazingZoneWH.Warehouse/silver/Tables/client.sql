CREATE TABLE [silver].[client] (
    [client_id]        INT            NOT NULL,
    [email]            VARCHAR (8000) NULL,
    [prenom]           VARCHAR (8000) NULL,
    [nom]              VARCHAR (8000) NULL,
    [genre]            VARCHAR (5)    NULL,
    [code_postal]      VARCHAR (8000) NULL,
    [ville]            VARCHAR (8000) NULL,
    [code_departement] VARCHAR (24)   NULL,
    [departement]      VARCHAR (8000) NULL,
    [region]           VARCHAR (8000) NULL,
    [date_inscription] DATE           NULL
);


GO