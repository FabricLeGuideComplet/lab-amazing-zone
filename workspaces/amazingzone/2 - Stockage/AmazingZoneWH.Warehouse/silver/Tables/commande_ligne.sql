CREATE TABLE [silver].[commande_ligne] (
    [ligne_id]         INT             NOT NULL,
    [commande_id]      INT             NOT NULL,
    [numero_commande]  VARCHAR (20)    NULL,
    [client_id]        INT             NOT NULL,
    [produit_id]       INT             NOT NULL,
    [date_commande]    DATETIME2 (6)   NOT NULL,
    [date_paiement]    DATETIME2 (6)   NULL,
    [statut_commande]  VARCHAR (20)    NULL,
    [statut_paiement]  VARCHAR (30)    NULL,
    [statut_livraison] VARCHAR (30)    NULL,
    [mode_livraison]   VARCHAR (50)    NULL,
    [quantite]         INT             NOT NULL,
    [prix_unitaire_ht] DECIMAL (18, 2) NULL,
    [montant_ht]       DECIMAL (18, 2) NULL,
    [cout_achat]       DECIMAL (18, 2) NULL
);


GO