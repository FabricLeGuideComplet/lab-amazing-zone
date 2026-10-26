-- =============================================================================
-- Rôle de lecture fabric_ingestion, utilisé par la connexion Fabric « PostgreSQL - WMS »
-- (passerelle de données locale) au lieu du superutilisateur postgres (chapitre 9).
--
-- Le mot de passe n'est jamais écrit dans ce fichier : il est passé en variable psql,
-- puis rangé dans le coffre de clés (secret wms-postgresql-fabric-ingestion).
--
--   sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres \
--        -v mot_de_passe="$MOT_DE_PASSE" -f init/role_fabric_ingestion.sql
--
-- Rejouable : oui (le rôle est créé s'il n'existe pas, sinon son mot de passe est changé).
-- =============================================================================

SELECT format('CREATE ROLE fabric_ingestion LOGIN PASSWORD %L', :'mot_de_passe')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fabric_ingestion') \gexec
ALTER ROLE fabric_ingestion LOGIN PASSWORD :'mot_de_passe';

GRANT CONNECT ON DATABASE postgres TO fabric_ingestion;
GRANT USAGE ON SCHEMA wms TO fabric_ingestion;
GRANT SELECT ON ALL TABLES IN SCHEMA wms TO fabric_ingestion;
-- Tables créées plus tard par les migrations : lecture accordée d'office
ALTER DEFAULT PRIVILEGES IN SCHEMA wms GRANT SELECT ON TABLES TO fabric_ingestion;
