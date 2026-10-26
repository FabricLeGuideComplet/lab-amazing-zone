CREATE TABLE [ml].[charge_entrepot_jour] (
    [code_entrepot]             VARCHAR (10) NULL,
    [jour]                      DATE         NULL,
    [nb_commandes]              INT          NULL,
    [nb_articles]               INT          NULL,
    [est_a_prevoir]             BIT          NULL,
    [jour_semaine]              SMALLINT     NULL,
    [mois]                      SMALLINT     NULL,
    [est_week_end]              INT          NULL,
    [est_periode_noel]          INT          NOT NULL,
    [temperature_max_prevue]    FLOAT (53)   NULL,
    [temperature_min_prevue]    FLOAT (53)   NULL,
    [precipitations_prevues_mm] FLOAT (53)   NULL,
    [neige_prevue_cm]           FLOAT (53)   NULL,
    [rafales_prevues_kmh]       FLOAT (53)   NULL,
    [est_intemperie_prevue]     INT          NOT NULL,
    [nb_commandes_j_moins_7]    INT          NULL,
    [moyenne_commandes_28j]     FLOAT (53)   NULL
);


GO