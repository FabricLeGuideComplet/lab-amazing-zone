CREATE TABLE [tech].[ingestWMS_config] (
    [src_code]       VARCHAR (300) NULL,
    [src_database]   VARCHAR (300) NULL,
    [src_schema]     VARCHAR (300) NULL,
    [src_table]      VARCHAR (300) NULL,
    [custom_query]   VARCHAR (MAX) NULL,
    [ingest_mode]    VARCHAR (300) NULL,
    [delta_col_name] VARCHAR (300) NULL,
    [delta_nb_jours] INT           NULL,
    [delta_key_cols] VARCHAR (300) NULL,
    [is_active]      BIT           NULL,
    [lake_name]      VARCHAR (300) NULL,
    [lake_schema]    VARCHAR (300) NULL,
    [lake_table]     VARCHAR (300) NULL,
    [wrh_table]      VARCHAR (300) NULL,
    [tech_upd_date]  DATETIME2 (6) NULL,
    [tech_upd_name]  VARCHAR (300) NULL
);


GO