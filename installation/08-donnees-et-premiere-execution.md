# 8. Données de démonstration et première exécution

Tout est en place ; il reste à remplir les sources, puis à faire tourner la chaîne de bout en bout une première
fois. L'ordre suit les dépendances : le générateur du site lit le référentiel géographique dans le Lakehouse, le
générateur du WMS lit les commandes du site.

Avant de commencer :

```bash
set -a; . ./.env; set +a
az vm start -g RG_WMS -n WMSpostgre
az vm start -g RG_WMS -n WMSgateway          # la passerelle met une à deux minutes à se signaler en ligne
```

## 8.1 Référentiels Excel

Dans l'espace de développement, ouvrez le Dataflow « Ingestion - Referentiels Excel » et lancez **Actualiser
maintenant** depuis l'interface, avec votre compte. Une actualisation déclenchée directement par le principal de
service échoue sans message exploitable ; lancée par le pipeline d'ingestion, elle réussit.

Contrôle, dans le point de terminaison SQL du Lakehouse :

```sql
SELECT COUNT(*) FROM referentiels.geographie;     -- 101 départements
SELECT COUNT(*), COUNT(DISTINCT [Code devise]) FROM referentiels.taux_change;   -- 1 984 lignes, 153 devises
```

## 8.2 Commandes du site e-commerce

```bash
pip install pyodbc
python ecommerce/donnees_demo/generer_commandes.py --purge
```

Le script, rejouable et à graine fixe, ajoute 600 clients français répartis sur les départements du référentiel,
environ 4 000 commandes de janvier 2025 à octobre 2026 (saisonnalité de fin d'année, statuts de paiement et de
livraison selon l'ancienneté) et un coût d'achat pour chaque produit. Les clients générés ont une adresse en
`@demo.amazingzone.fr` ; `--purge` supprime ceux d'une exécution précédente avant de régénérer.

Remettez ensuite les prix d'origine des trois produits qui serviront à la démonstration de l'historisation
(section 8.7), avant le premier chargement de la couche Gold :

```bash
sqlcmd -S $AMAZINGZONE_SQL_SERVEUR -d amazingdb --authentication-method ActiveDirectoryDefault \
   -i ecommerce/donnees_demo/prix_origine.sql
```

La commande suppose [go-sqlcmd](https://learn.microsoft.com/sql/tools/sqlcmd/go-sqlcmd-utility) et une session
`az login` avec un compte membre de `dp-equipedata` ; l'éditeur de requêtes du portail Azure convient aussi.

Le mirroring réplique les nouvelles lignes en quelques minutes. Dans l'espace « AmazingZone - Mirroring », la page
**Surveiller la réplication** de `amazingdb` doit afficher environ 4 065 lignes pour `Order`.

## 8.3 Données du WMS

Le générateur du WMS reconstruit les tables transactionnelles à partir des commandes du site : mêmes numéros de
commande, un article par produit du catalogue, une commande logistique par commande payée, préparée dans
l'entrepôt le plus proche de la région du client, une expédition par commande expédiée.

```bash
python wms/donnees_demo/generer_wms.py > wms/donnees_demo/wms_demo.sql
IP_PG=$(az vm show -d -g RG_WMS -n WMSpostgre --query publicIps -o tsv)
scp -i ~/.ssh/wmspostgre_ed25519 wms/donnees_demo/wms_demo.sql azureuser@$IP_PG:~/wms/donnees_demo/
ssh -i ~/.ssh/wmspostgre_ed25519 azureuser@$IP_PG \
   "sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f ~/wms/donnees_demo/wms_demo.sql"
```

Le fichier `wms_demo.sql` versionné correspond aux données de l'auteur ; régénérez-le comme ci-dessus pour qu'il
corresponde aux vôtres. Avec le jeu de l'auteur, le WMS compte 3 897 commandes, 3 734 expéditions, 47 articles et
376 lignes de stock :

```bash
ssh -i ~/.ssh/wmspostgre_ed25519 azureuser@$IP_PG "sudo -u postgres psql -d postgres -c \
  'SELECT (SELECT COUNT(*) FROM wms.orders) commandes, (SELECT COUNT(*) FROM wms.shipment) expeditions'"
```

## 8.4 Historique météo

Exécutez une fois le notebook « Ingestion - Météo historique » (dossier « 1 - Ingestion »). Il charge l'historique
des observations et des prévisions émises par le modèle Météo-France pour les quatre entrepôts, à partir des API
*historical forecast* et *previous runs* d'Open-Meteo, dans `meteo.weather_forecast` et
`meteo.weather_forecast_issued`. Les rafales prévues ne sont archivées par Open-Meteo que depuis le 7 août 2026.

## 8.5 Première ingestion et transformation

Lancez le pipeline « Orchestration - Ingestion » avec le paramètre `forcer_tout` à `true` : sans lui, les
branches météo, référentiels et transformation ne s'exécutent qu'à 6 h (et le lundi pour les référentiels).

| Étape | Élément | Durée observée dans le lab |
|---|---|---|
| Ingestion WMS | Copy Job « Ingestion - WMS » (8 tables, instantané puis incrémental sur `date_maj`) | 2 à 3 minutes |
| Prévisions météo | Activité Web « Cle API meteo » (coffre), puis notebook « Ingestion - Météo » | 1 à 2 minutes |
| Référentiels | Dataflow « Ingestion - Referentiels Excel » | 1 à 2 minutes |
| Transformation | Pipeline « Orchestration - Transformation » : synchronisation du point de terminaison SQL, job dbt (`build`, avertissements exclus), recadrage du modèle sémantique | 6 à 8 minutes, dont 4 pour le job dbt |

Le pipeline « Orchestration - Transformation » se lance aussi seul, une fois les données en place.

### Vérifier

Dans le Warehouse `AmazingZoneWH` (attention : le Warehouse est sensible à la casse, noms de tables compris) :

```sql
SELECT 'DimClient' AS objet, COUNT(*) AS lignes FROM gold.DimClient
UNION ALL SELECT 'FaitVente', COUNT(*) FROM gold.FaitVente
UNION ALL SELECT 'FaitExpedition', COUNT(*) FROM gold.FaitExpedition
UNION ALL SELECT 'FaitMeteoJour', COUNT(*) FROM gold.FaitMeteoJour;

-- Chiffre d'affaires hors taxes 2026, commandes annulées exclues
SELECT CAST(SUM(MontantHT) AS INT) AS ca_ht_2026
FROM gold.FaitVente
WHERE DateCommandeId BETWEEN 20260101 AND 20261231 AND StatutCommande <> 'Annulée';
```

Ordres de grandeur dans le lab de l'auteur : 607 lignes dans `DimClient` (les 606 clients et le membre inconnu),
5 163 lignes de vente, 3 897 expéditions et environ 662 600 € de chiffre d'affaires hors taxes en 2026, le chiffre
que cite le chapitre 2. Les tables météo et `FaitStockJour` dépendent de la date d'exécution.

Ouvrez ensuite le rapport « Pilotage des ventes et de la logistique » : ses cinq pages (Ventes, Logistique et
météo, Budget et réalisé, Stock et service client, Saisie des objectifs) doivent s'afficher sans erreur.

## 8.6 Temps réel

### Journaux du site

Naviguez quelques minutes sur la boutique (pages produits, panier, quelques adresses inexistantes pour produire
des erreurs 404). Après deux à cinq minutes, dans la base KQL `AmazingZoneEH` :

```kusto
fn_ParseWebLogs()
| summarize requetes = count(), erreurs = countif(Success == false) by bin(dateLog, 5m)
| order by dateLog desc
```

La vue **Data insights** de l'Eventstream « Flux - Journaux du site » est le moyen le plus rapide de vérifier qu'une
destination écrit bien.

### Événements du WMS

```bash
pip install azure-eventhub
python wms/temps_reel/simulateur_evenements.py --par-minute 60 --duree 10
```

Le simulateur lit la chaîne de connexion de la source `WMSEvent` par l'API Fabric, avec le principal de service
(`FABRIC_ESPACE_ID`, `WMS_EVENTSTREAM_ID`, `WMS_EVENTSTREAM_SOURCE_ID`), ou directement dans la variable
`WMS_EVENTSTREAM_CS` si vous la renseignez (Eventstream > source WMSEvent > Event Hub > Clés). Latence mesurée dans
le lab : environ 7 secondes jusqu'à la table `wms_events`.

```kusto
wms_events
| summarize count() by eventType, warehouse
```

## 8.7 Historisation des prix (chapitre 5)

```bash
sqlcmd -S $AMAZINGZONE_SQL_SERVEUR -d amazingdb --authentication-method ActiveDirectoryDefault \
   -i ecommerce/donnees_demo/changer_prix.sql
```

Le script modifie le prix de trois produits. Après le passage du mirroring et une nouvelle exécution
d'« Orchestration - Transformation », `snapshots.produit` et `gold.DimProduit` contiennent une seconde version de
ces produits, avec ses dates de validité.

## 8.8 Variante en vues matérialisées (facultatif)

Exécutez le notebook « Variante - Silver en vues matérialisées » : il crée les sept vues Silver dans le schéma
`silver_mlv` du Lakehouse. Rafraîchissez ensuite le lignage du Lakehouse ; les métriques de chaque
rafraîchissement sont dans `_mlv_system.sys_node_metrics`. Cette variante n'est pas appelée par l'orchestration.

## 8.9 Planification

Le dépôt n'enregistre aucune planification : le lab ne consomme de capacité que lorsque vous lancez les pipelines.
Pour reproduire le fonctionnement décrit au chapitre 4, ajoutez une planification horaire à « Orchestration -
Ingestion » ; elle déclenche la transformation à 6 h. Pensez à la retirer en fin de séance, et à arrêter les VM
(guide 9) : une ingestion WMS lancée VM éteinte échoue avec `GatewayUnreachable`.
