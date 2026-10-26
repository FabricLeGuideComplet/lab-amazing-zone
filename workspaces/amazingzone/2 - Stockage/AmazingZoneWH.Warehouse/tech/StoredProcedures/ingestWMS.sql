CREATE   PROCEDURE tech.ingestWMS
AS
BEGIN

   DECLARE @proc_upd_date datetime2(6) = GETDATE()
   DECLARE @proc_upd_name varchar(300) = 'ingestWMS'

    drop table if exists tech.ingestWMS_config

    create table tech.ingestWMS_config
    (
        src_code varchar(300), 
        src_database varchar(300), 
        src_schema varchar(300), 
        src_table varchar(300), 
        custom_query varchar(MAX), 
        ingest_mode varchar(300), 
        delta_col_name varchar(300), 
        delta_nb_jours int, 
        delta_key_cols varchar(300), 
        is_active bit, 
        lake_name varchar(300), 
        lake_schema varchar(300), 
        lake_table varchar(300), 
        wrh_table varchar(300),          -- table Silver du Warehouse alimentée (lignage, documentation)
        tech_upd_date datetime2(6),
        tech_upd_name varchar(300)
    )


    insert into tech.ingestWMS_config
    values 
        ('wms', 'postgres', 'wms', 'customer', null, 'FULL', null, null, null, 1, 'AmazingZoneLK', 'wms_mdp', 'customer', NULL, @proc_upd_date, @proc_upd_name),
        ('wms', 'postgres', 'wms', 'inventory', null, 'DELTA', 'date_maj', 3, 'inventory_id', 1, 'AmazingZoneLK', 'wms_mdp', 'inventory', 'stock', @proc_upd_date, @proc_upd_name),
        ('wms', 'postgres', 'wms', 'item', null, 'FULL', null, null, null, 1, 'AmazingZoneLK', 'wms_mdp', 'item', 'stock', @proc_upd_date, @proc_upd_name),
        ('wms', 'postgres', 'wms', 'location', null, 'FULL', null, null, null, 1, 'AmazingZoneLK', 'wms_mdp', 'location', 'stock', @proc_upd_date, @proc_upd_name),
        ('wms', 'postgres', 'wms', 'order_line', null, 'DELTA', 'date_maj', 3, 'order_line_id', 1, 'AmazingZoneLK', 'wms_mdp', 'order_line', 'commande_logistique', @proc_upd_date, @proc_upd_name),
        ('wms', 'postgres', 'wms', 'orders', 'select * from wms.orders where status = ''CREATED''', 'FULL', null, null, null, 1, 'AmazingZoneLK', 'wms_mdp', 'orders', 'commande_logistique', @proc_upd_date, @proc_upd_name), 
        ('wms', 'postgres', 'wms', 'shipment', null, 'FULL', null, null, null, 1, 'AmazingZoneLK', 'wms_mdp', 'shipment', 'commande_logistique', @proc_upd_date, @proc_upd_name),        
        ('wms', 'postgres', 'wms', 'warehouse', null, 'FULL', null, null, null, 1, 'AmazingZoneLK', 'wms_mdp', 'warehouse', 'entrepot', @proc_upd_date, @proc_upd_name)

END

GO