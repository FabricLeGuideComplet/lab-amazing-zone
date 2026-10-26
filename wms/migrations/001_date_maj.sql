-- =============================================================================
-- Migration 001 : ajout d'une colonne date_maj et d'un trigger de mise à jour
-- sur les tables métier du schéma wms.
--
-- Objectif : disposer d'une colonne fiable pour les chargements incrémentaux
-- (watermark du Copy Job, mode DELTA du pipeline « Ingestion - WMS par métadonnées »).
-- La colonne est renseignée à l'insertion par sa valeur par défaut, puis
-- mise à jour par trigger à chaque modification, quel que soit le programme
-- à l'origine de l'UPDATE.
--
-- Rejouable : oui (IF NOT EXISTS / OR REPLACE / DROP TRIGGER IF EXISTS).
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION wms.maj_date_maj()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
   NEW.date_maj := now();
   RETURN NEW;
END;
$$;

DO $$
DECLARE
   t text;
BEGIN
   FOREACH t IN ARRAY ARRAY['warehouse', 'location', 'item', 'customer',
                            'inventory', 'orders', 'order_line', 'shipment']
   LOOP
      EXECUTE format(
         'ALTER TABLE wms.%I ADD COLUMN IF NOT EXISTS date_maj timestamptz NOT NULL DEFAULT now()', t);
      EXECUTE format(
         'DROP TRIGGER IF EXISTS trg_%s_date_maj ON wms.%I', t, t);
      EXECUTE format(
         'CREATE TRIGGER trg_%s_date_maj BEFORE UPDATE ON wms.%I
             FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj()', t, t);
      EXECUTE format(
         'CREATE INDEX IF NOT EXISTS ix_%s_date_maj ON wms.%I (date_maj)', t, t);
   END LOOP;
END;
$$;

COMMIT;
