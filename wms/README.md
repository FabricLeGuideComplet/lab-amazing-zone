# WMS – base PostgreSQL

Code de la base du WMS d'Amazing Zone, source on-premise de la plateforme Fabric
(VM `WMSpostgre`, PostgreSQL 16, base `postgres`, schéma `wms`).

## Contenu

| Dossier | Rôle |
|---|---|
| `init/` | Script de création initiale du schéma et des données de démonstration (`wms_init.sql`), rôle de lecture `fabric_ingestion` utilisé par Fabric (`role_fabric_ingestion.sql`). |
| `migrations/` | Évolutions du schéma, à appliquer dans l'ordre après `init/`. Chaque script est rejouable. |
| `schema/` | État de référence du schéma (`pg_dump --schema-only`), régénéré après chaque migration. |
| `donnees_demo/` | Jeu de démonstration cohérent avec le site e-commerce (`wms_demo.sql`) et son générateur (`generer_wms.py`). |

## Migrations

| N° | Script | Objet |
|---|---|---|
| 001 | `001_date_maj.sql` | Colonne `date_maj` (timestamptz, défaut `now()`), trigger `BEFORE UPDATE` et index sur les 8 tables métier, pour les chargements incrémentaux (Copy Job, mode DELTA du pipeline « Ingestion - WMS par métadonnées » et Copy Job « Ingestion - WMS »). |
| 002 | `002_entrepot_commande.sql` | Colonne `warehouse_id` sur `wms.orders` : entrepôt de préparation de la commande (4 entrepôts). |

## Appliquer

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f init/wms_init.sql
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f migrations/001_date_maj.sql
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f migrations/002_entrepot_commande.sql
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f donnees_demo/wms_demo.sql
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -v mot_de_passe="$MOT_DE_PASSE" -f init/role_fabric_ingestion.sql
```

L'installation de la VM et de PostgreSQL est décrite dans `installation/03-wms-postgresql-et-passerelle.md`, la
création du rôle et de son secret dans `installation/05-coffre-de-cles.md`.

## Données de démonstration

`donnees_demo/wms_demo.sql` vide les tables transactionnelles (articles, clients, stock, commandes, lignes,
expéditions) puis les recharge à partir des commandes du site e-commerce : mêmes numéros de commande
(`order_no` = `CustomOrderNumber`), un article par produit du catalogue (`sku` = `Product.Sku`), quatre
entrepôts (WH1 à WH4, ceux de l'ingestion météo), une expédition par commande expédiée. Le fichier est
versionné pour que le lab se rejoue à l'identique ; `generer_wms.py` le régénère si la base e-commerce change
(`python generer_wms.py > wms_demo.sql`, avec les variables du principal de service du lab).

## Régénérer le schéma de référence

```bash
sudo -u postgres pg_dump -d postgres -n wms --schema-only --no-owner --no-privileges > schema/wms_schema.sql
```
