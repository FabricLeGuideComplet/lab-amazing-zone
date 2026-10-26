# Modélisation et transformation (chapitre 5)

Chaîne de transformation d'Amazing Zone, de la couche brute au modèle sémantique. Les couches Silver et Gold sont
construites par **dbt dans le Warehouse** ; une variante de la couche Silver en Materialized Lake Views est
documentée et déployable à part (schéma `silver_mlv`).

| Couche | Élément | Contenu |
|---|---|---|
| Bronze | `AmazingZoneLK`, un schéma par système source : `ecommerce` (raccourcis vers la base mirrorée `amazingdb` de l'espace « AmazingZone - Mirroring »), `wms` (Copy Job), `wms_mdp` (Metadata Driven Pipeline), `meteo` (`weather_forecast`, `weather_forecast_issued`), `referentiels` (`geographie`, `taux_change`) | Données telles qu'ingérées (chapitre 4) |
| Silver | `AmazingZoneWH` schéma `silver`, construit par le job dbt « Silver et Gold - Nettoyage et modèle en étoile » | `client`, `produit`, `commande_ligne`, `commande_logistique`, `stock`, `entrepot`, `meteo_jour`, `taux_change` (QUALIFY), seed `coordonnees_entrepots` |
| Gold | `AmazingZoneWH` schémas `gold` et `snapshots` (même job dbt) | Modèle en étoile : `DimDate`, `DimClient` (SCD 1), `DimProduit` (SCD 2 par le snapshot `snapshot_produit`, table `snapshots.produit`), `DimEntrepot`, `DimTransporteur`, `FaitVente`, `FaitExpedition`, `FaitStockJour` (photo quotidienne, incrémental), `FaitMeteoJour` |
| ML | `AmazingZoneWH` schéma `ml` (même job dbt) | `charge_entrepot_jour` : table de caractéristiques pour prévoir la charge des entrepôts (prévision météo émise la veille, historique arrêté à J-2) |
| Sémantique | « Ventes et logistique » | Modèle Direct Lake sur OneLake, mesures et descriptions ; mises à jour automatiques désactivées, recadrage en fin de pipeline |
| Variante | `AmazingZoneLK` schéma `silver_mlv`, notebook « Variante - Silver en vues matérialisées » | Les sept vues Silver en Materialized Lake Views, avec `REFRESH_HINT` (préversion) ; non appelée par l'orchestration |

Le projet dbt (19 modèles dont `api.stock_disponible` ajouté au chapitre 6, 1 seed, 1 snapshot, 78 tests dont 3 en sévérité `warn` étiquetés `avertissement`) vit
dans le dossier de l'élément : `workspaces/amazingzone/3 - Transformation/Silver et Gold - Nettoyage et modèle en étoile.DataBuildToolJob/Code/dbt`.
C'est la seule source du projet ; développer en local sur un clone de ce dossier.

## Orchestration

- « Orchestration - Ingestion » (toutes les heures) : Copy Job WMS, prévisions météo à 6 h, référentiels Excel le
  lundi à 6 h ; à 6 h, une fois les trois réussis, appelle « Orchestration - Transformation » (Invoke pipeline,
  connexion « Pipeline - SP AmazingZone »).
- « Orchestration - Transformation » : notebook « Bronze - Synchronisation SQL » (synchronise le point de terminaison
  SQL du Lakehouse, échoue si une table n'est pas synchronisée) → job dbt (`build`, `exclude: tag:avertissement`,
  connexion « dbt job - SP AmazingZone ») → actualisation du modèle sémantique (connexion « Modèle sémantique - SP
  AmazingZone »).

## Rejouer le lab

1. Données de démonstration : `ecommerce/donnees_demo/generer_commandes.py --purge`, puis sur la VM du WMS
   `wms/migrations/002_entrepot_commande.sql` et `wms/donnees_demo/wms_demo.sql`.
2. Ingestion : pipeline « Orchestration - Ingestion » avec `forcer_tout` (chapitre 4) ; historique météo et
   prévisions de la veille : notebook « Ingestion - Météo historique » (exécution ponctuelle, API historical
   forecast et previous runs d'Open-Meteo ; les rafales prévues par Météo-France ne sont archivées que depuis le
   7 août 2026).
3. Raccourcis `ecommerce` dans AmazingZoneLK vers les tables `Customer`, `Order`, `OrderItem`, `Product`, `Category`
   et `Product_Category_Mapping` de la base mirrorée (six tables mirrorées à la création au chapitre 4, dont `ProductWarehouseInventory`, non utilisée ; `Product_Category_Mapping` ajoutée au mirroring au chapitre 5).
4. Transformation : `ecommerce/donnees_demo/prix_origine.sql`, puis pipeline « Orchestration - Transformation » (ou le
   job dbt seul). Attention : le Warehouse et le point de terminaison SQL sont sensibles à la casse (noms de tables
   compris).
5. Historisation : `ecommerce/donnees_demo/changer_prix.sql` modifie trois prix ; après la transformation suivante,
   `snapshots.produit` et `gold.DimProduit` contiennent une nouvelle version de ces produits.
6. Variante MLV (facultatif) : exécuter le notebook « Variante - Silver en vues matérialisées », puis rafraîchir le
   lignage du Lakehouse ; les métriques de chaque rafraîchissement sont dans `_mlv_system.sys_node_metrics`.

## Identités et connexions du labo (état au 22/10/2026)

| Élément | Identité | Connexion Fabric |
|---|---|---|
| Base mirrorée `amazingdb` (espace AmazingZone - Mirroring) | identité de l'espace de travail AmazingZone - Mirroring, utilisateur `[AmazingZone - Mirroring]` dans amazingdb (créé `WITH SID`, le serveur n'ayant pas le rôle Directory Readers), droits SELECT, ALTER ANY EXTERNAL MIRROR, VIEW DATABASE PERFORMANCE STATE, VIEW DATABASE SECURITY STATE | « SQL - NopCommerce (identité AmazingZone - Mirroring) » |
| Eventstream « Flux - Journaux du site » | stratégie d'accès partagé `fabric-listen` (Listen) de l'Event Hub weblogs, groupe de consommateurs `fabric` | « Event Hub - Journaux du site (fabric-listen) » |
| Pipelines, job dbt, modèle sémantique, Copy Job | principal de service SP-Fabric-AmazingZone | « Pipeline - SP AmazingZone », « dbt job - SP AmazingZone », « Modèle sémantique - SP AmazingZone », « Copy job - SP AmazingZone » |
| Lien Fabric Dataverse | identité de l'espace AmazingZone - Dev - Marie (choix discuté au chapitre 4) | « Dataverse - CustomerService » |

Les deux espaces sont rattachés au domaine « Commerce » (administré par le groupe dp-equipedata).

