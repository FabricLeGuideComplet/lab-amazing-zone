CREATE TABLE [silver].[commande_logistique] (
    [commande_wms_id]      BIGINT         NULL,
    [numero_commande]      VARCHAR (20)   NULL,
    [code_entrepot]        VARCHAR (10)   NULL,
    [statut_logistique]    VARCHAR (20)   NULL,
    [date_prise_en_charge] DATETIME2 (6)  NULL,
    [date_expedition]      DATETIME2 (6)  NULL,
    [transporteur]         VARCHAR (50)   NULL,
    [numero_suivi]         VARCHAR (8000) NULL,
    [nb_lignes]            INT            NULL,
    [nb_articles]          INT            NULL
);


GO