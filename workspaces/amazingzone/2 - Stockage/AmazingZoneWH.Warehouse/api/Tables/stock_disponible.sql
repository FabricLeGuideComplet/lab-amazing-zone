CREATE TABLE [api].[stock_disponible] (
    [sku]                 VARCHAR (50)  NOT NULL,
    [code_entrepot]       VARCHAR (10)  NOT NULL,
    [quantite_disponible] INT           NULL,
    [date_maj_wms]        DATETIME2 (6) NULL
);


GO

ALTER TABLE [api].[stock_disponible]
    ADD CONSTRAINT [pk_stock_disponible] PRIMARY KEY NONCLUSTERED ([sku] ASC, [code_entrepot] ASC) NOT ENFORCED;


GO