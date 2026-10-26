-- =============================================================================
-- Migration 002 : entrepôt de préparation des commandes.
--
-- Amazing Zone exploite quatre entrepôts. Chaque commande logistique est
-- préparée dans un seul d'entre eux : la colonne warehouse_id porte ce
-- rattachement, indispensable pour analyser les expéditions par site.
--
-- Rejouable : oui (IF NOT EXISTS).
-- =============================================================================

BEGIN;

ALTER TABLE wms.orders ADD COLUMN IF NOT EXISTS warehouse_id bigint
   REFERENCES wms.warehouse(warehouse_id);

CREATE INDEX IF NOT EXISTS ix_orders_warehouse_id ON wms.orders(warehouse_id);

COMMIT;
