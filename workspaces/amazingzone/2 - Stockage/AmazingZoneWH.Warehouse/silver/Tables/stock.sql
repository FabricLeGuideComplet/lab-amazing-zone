CREATE TABLE [silver].[stock] (
    [sku]               VARCHAR (50)    NULL,
    [code_entrepot]     VARCHAR (10)    NULL,
    [quantite_stock]    DECIMAL (38, 3) NULL,
    [quantite_reservee] DECIMAL (38, 3) NULL,
    [date_maj]          DATETIME2 (6)   NULL
);


GO