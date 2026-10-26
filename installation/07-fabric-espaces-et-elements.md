# 7. Espaces et éléments Fabric

Ce guide met en place la partie Fabric : capacité, espaces de travail, identités, connexions et mirroring, puis
déploie les éléments du dossier `workspaces/amazingzone` dans votre espace. L'ordre compte : les connexions et la
base mirrorée doivent exister avant le déploiement, car les éléments y font référence par leur identifiant.

## 7.1 Capacité

| Option | Quand la choisir |
|---|---|
| Capacité d'évaluation (Trial) | Si votre locataire y a droit : 60 jours, équivalent F64, gratuite. Activez-la depuis le portail Fabric (Gestionnaire de compte > Démarrer l'essai). |
| Capacité F2 ou plus | Ressource Azure `Microsoft.Fabric/capacities`, dans la région du lab (France Central). La F2 suffit pour les volumes du lab, au prix de temps d'exécution plus longs quand le job dbt et un notebook Spark tournent en même temps. Suspendez-la en dehors des séances (guide 9). |

Dans le lab de l'auteur, l'espace de développement est sur une capacité d'évaluation et l'espace du mirroring sur
une F2. La capacité de l'espace qui reçoit le lien Dataverse doit être dans la même zone géographique que
l'environnement Dataverse (guide 6).

## 7.2 Espaces de travail

| Espace | Rôle | Git |
|---|---|---|
| `AmazingZone - Dev - <prénom>` | Espace de développement de la plateforme : tous les éléments du dépôt | Oui, dossier `workspaces/amazingzone` |
| `AmazingZone - Mirroring` | Base mirrorée `amazingdb`, isolée pour que ses droits et sa consommation se lisent à part (chapitre 4) | Non |

Pour chacun des deux espaces :

1. Créez l'espace et affectez-le à la capacité.
2. **Gérer l'accès** : ajoutez `dp-equipedata` avec le rôle Membre, et `SP-Fabric-AmazingZone` avec le rôle
   Membre ou Administrateur (le déploiement par fabric-cicd l'exige).
3. Paramètres de l'espace > **Identité de l'espace de travail** > + Identité de l'espace de travail. Notez son ID
   d'application : il sert au mirroring (espace Mirroring) et au lien Dataverse (espace Dev).

Pour l'espace de développement seulement :

4. Donnez à son identité le rôle **Contributeur** sur l'espace lui-même : l'activité dbt du pipeline
   « Orchestration - Transformation » l'utilise.
5. Paramètres de l'espace > Ingénierie des données/science > Spark : le profil `writeHeavy` (V-Order désactivé)
   est celui des nouveaux espaces ; le lab le conserve, le chapitre 5 explique pourquoi.

Facultatif, pour la gouvernance (chapitre 3) : Portail d'administration > **Domaines** > créez le domaine
`Commerce`, administré par `dp-equipedata`, et rattachez-y les deux espaces.

## 7.3 Connexions

Fabric > Paramètres > **Gérer les connexions et les passerelles** > Nouveau. Créez les connexions ci-dessous, puis,
pour chacune, **Gérer les utilisateurs** : ajoutez `SP-Fabric-AmazingZone` et `dp-equipedata` avec le rôle
Utilisateur. Une connexion non partagée avec le principal de service fait échouer les exécutions qu'il porte et
les mises à jour de définition par API.

Relevez l'identifiant de chaque connexion (Paramètres de la connexion > ID de connexion) et reportez-le dans `.env`.

| Connexion | Type | Paramètres | Authentification | Utilisée par | Variable `.env` |
|---|---|---|---|---|---|
| `PostgreSQL - WMS` | Passerelle locale `WMSgateway`, PostgreSQL | Serveur `10.0.0.4`, base `postgres`, chiffrement non requis (trafic interne au réseau virtuel) | Basique : utilisateur `fabric_ingestion`, mot de passe lu par la référence `kv-amazingzone-lab`, secret `wms-postgresql-fabric-ingestion` | Copy Job « Ingestion - WMS » | `CONNEXION_POSTGRESQL_WMS` |
| `Copy job - SP AmazingZone` | Copy job | | Principal de service (ID locataire, ID client, secret) | Activité Copy job d'« Orchestration - Ingestion » | `CONNEXION_COPYJOB_SP` |
| `Pipeline - SP AmazingZone` | Pipelines de données Fabric | | Principal de service | Activité Invoke pipeline (Ingestion → Transformation) | `CONNEXION_PIPELINE_SP` |
| `dbt job - SP AmazingZone` | Job dbt | | Principal de service | Activité dbt d'« Orchestration - Transformation » | `CONNEXION_DBT_SP` |
| `Modèle sémantique - SP AmazingZone` | Modèles sémantiques Power BI | | Principal de service | Activité d'actualisation du modèle « Ventes et logistique » | `CONNEXION_MODELE_SEMANTIQUE_SP` |
| `Key Vault - SP AmazingZone` | Web v2 | URL de base `https://<coffre>.vault.azure.net/`, audience `https://vault.azure.net` | Principal de service avec certificat, lu par la référence `kv-amazingzone-lab` (certificat `cert-sp-fabric-sharepoint`) | Activité Web « Cle API meteo » | `CONNEXION_KEYVAULT_SP` |
| `SharePoint - Finance (SP AmazingZone)` | Web | URL du site `https://<locataire>.sharepoint.com/sites/Finance` | Principal de service avec certificat, par la référence `kv-amazingzone-lab`. Créez-la avec **Ignorer le test de connexion** : le test échoue alors que la connexion fonctionne | Dataflow « Ingestion - Referentiels Excel » | liée à la main (section 7.6) |
| `Event Hub - Journaux du site (fabric-listen)` | Azure Event Hubs | Espace de noms `<espace de noms>.servicebus.windows.net`, Event Hub `weblogs` | Clé d'accès partagé : stratégie `fabric-listen` et sa clé primaire | Eventstream « Flux - Journaux du site » | `CONNEXION_EVENTHUB_JOURNAUX` |
| `SQL - NopCommerce (identité AmazingZone - Mirroring)` | Azure SQL Database | Serveur `<serveur>.database.windows.net`, base `amazingdb` | Identité de l'espace de travail | Mirroring (section 7.4) | |
| `SQL - NopCommerce` (facultatif) | Azure SQL Database | Même serveur et base | Principal de service | Copy Job archivé « Ingestion - NopCommerce » | `CONNEXION_SQL_NOPCOMMERCE_SP` |

La clé primaire de `fabric-listen` se lit dans le portail Azure (Event Hub `weblogs` > Stratégies d'accès partagé)
ou par `az eventhubs eventhub authorization-rule keys list -g RG_AmazingZone --namespace-name <espace de noms> --eventhub-name weblogs -n fabric-listen --query primaryKey -o tsv`.

Si vous ne déployez pas les éléments archivés, donnez à `CONNEXION_SQL_NOPCOMMERCE_SP` la valeur
`00000000-0000-0000-0000-000000000000` : le fichier de paramètres exige que la variable existe.

## 7.4 Mirroring de la base du site

### Utilisateur de l'identité de l'espace dans amazingdb

Connecté à `amazingdb` avec un compte membre de `dp-equipedata`, créez l'utilisateur de l'identité de l'espace
« AmazingZone - Mirroring » à partir de son ID d'application (section 7.2), puis accordez les droits que le
mirroring exige :

```sql
DECLARE @sid NVARCHAR(100) = CONVERT(NVARCHAR(100),
        CONVERT(VARBINARY(16), CAST('<ID d''application de l''identité de l''espace>' AS UNIQUEIDENTIFIER)), 1);
EXEC ('CREATE USER [AmazingZone - Mirroring] WITH SID = ' + @sid + ', TYPE = E');

GRANT SELECT, ALTER ANY EXTERNAL MIRROR, VIEW DATABASE PERFORMANCE STATE, VIEW DATABASE SECURITY STATE
   TO [AmazingZone - Mirroring];
```

Si l'identité du serveur SQL a le rôle *Directory Readers*, `CREATE USER [AmazingZone - Mirroring] FROM EXTERNAL
PROVIDER` suffit.

### Base mirrorée

Dans l'espace « AmazingZone - Mirroring » : Nouvel élément > **Base de données Azure SQL mise en miroir** :

1. Connexion : `SQL - NopCommerce (identité AmazingZone - Mirroring)`.
2. Désactivez **Mettre en miroir toutes les données** et la mise en miroir automatique des futures tables, puis
   sélectionnez : `Customer`, `Order`, `OrderItem`, `Product`, `Category`, `ProductWarehouseInventory` et
   `Product_Category_Mapping`. Une base nopCommerce compte plus d'une centaine de tables techniques sans intérêt
   analytique ; le chapitre 4 justifie la sélection.
3. Nommez la base mirrorée `amazingdb`, créez-la et attendez l'état **En cours d'exécution** pour les sept tables
   (cinq minutes environ).

Relevez dans l'URL de la base mirrorée (`/groups/<espace>/mirroreddatabases/<id>`) les deux identifiants et
reportez-les dans `.env` : `FABRIC_ESPACE_MIRRORING_ID` et `MIRRORING_AMAZINGDB_ID`. Ils servent aux raccourcis
`ecommerce` du Lakehouse.

À ce stade, la base ne contient que les données d'exemple de nopCommerce ; les commandes générées au guide 8
seront répliquées au fil de l'eau.

## 7.5 Déployer les éléments

Le script `installation/deployer_fabric.py` publie les éléments du dépôt dans votre espace avec
[fabric-cicd](https://microsoft.github.io/fabric-cicd/), la bibliothèque de déploiement de Microsoft. Le fichier
`workspaces/amazingzone/parameter.yml` y remplace les identifiants de l'environnement de l'auteur :

- les références entre éléments du dépôt (Lakehouse par défaut des notebooks, Warehouse du modèle sémantique,
  base KQL, point de terminaison SQL, tableau de bord surveillé par l'alerte) sont résolues vers les éléments
  déployés dans votre espace ;
- les connexions, la base mirrorée et l'hôte SharePoint sont lus dans vos variables d'environnement.

```bash
pip install fabric-cicd azure-identity
set -a; . ./.env; set +a
python installation/deployer_fabric.py --espace <ID de l'espace AmazingZone - Dev - prénom>
```

Le script publie les éléments dans l'ordre des dépendances (stockage, puis ingestion, transformation, restitution
et temps réel) et recrée les dossiers de l'espace. Les éléments du dossier « 9 - Archives » ne sont publiés
qu'avec `--avec-archives`.

| Dossier | Éléments déployés |
|---|---|
| 1 - Ingestion | Copy Job `Ingestion - WMS`, Dataflow `Ingestion - Referentiels Excel`, notebooks `Ingestion - Météo` et `Ingestion - Météo historique`, pipeline `Orchestration - Ingestion` |
| 2 - Stockage | Lakehouse `AmazingZoneLK` (schémas activés, raccourcis `ecommerce`), Warehouse `AmazingZoneWH` (projet SQL : schémas, tables, procédure `tech.ingestWMS`), Eventhouse `AmazingZoneEH` et sa base KQL (tables `logsweb`, `wms_events`, `sensors`, fonction `fn_ParseWebLogs`) |
| 3 - Transformation | Job dbt `Silver et Gold - Nettoyage et modèle en étoile`, notebooks `Bronze - Synchronisation SQL` et `Variante - Silver en vues matérialisées`, pipeline `Orchestration - Transformation` |
| 4 - Restitution | Modèles sémantiques `Ventes et logistique` et `Analyse des journaux du site`, rapports `Pilotage des ventes et de la logistique` et `Analyse des journaux du site`, API GraphQL `API_Stock_disponible`, fonctions de données `Saisie - Objectifs de vente` et `Service - Stock disponible` |
| 5 - Temps réel | Eventstreams `Flux - Journaux du site` et `Flux - Événements WMS`, ensemble de requêtes `Requêtes - Exploration KQL`, tableau de bord `Tableau de bord - Journaux du site`, alerte `Alerte - Disponibilité du site` |

Si une publication échoue, le message de fabric-cicd nomme l'élément. Les causes les plus fréquentes : une variable
de `.env` vide ou erronée, une connexion non partagée avec le principal de service, une base mirrorée absente pour
les raccourcis. Corrigez et relancez : le script met à jour les éléments déjà publiés.

### Synchroniser ensuite l'espace avec votre dépôt (facultatif)

Pour travailler comme l'auteur, avec un espace synchronisé avec Git, créez une branche vide dans votre copie du
dépôt (ou un dossier vide), connectez-y l'espace déjà déployé (Paramètres de l'espace > Intégration Git, dossier
de votre choix), puis validez depuis l'espace. Ne connectez pas l'espace au dossier `workspaces/amazingzone`
d'origine : il contient les identifiants de l'auteur, que seul le déploiement par fabric-cicd remplace.

## 7.6 Configuration après déploiement

Certains réglages ne passent pas par les définitions d'éléments et se font à la main, une fois :

| Élément | À faire |
|---|---|
| Dataflow `Ingestion - Referentiels Excel` | Ouvrir l'élément, **Configurer la connexion** : les sources SharePoint vers `SharePoint - Finance (SP AmazingZone)`, la destination Lakehouse vers votre compte (OAuth). Enregistrer et publier. Un nom de Dataflow ne peut pas contenir d'accent, d'où « Referentiels ». |
| Copy Job `Ingestion - WMS` | Ouvrir l'élément et vérifier que la source utilise `PostgreSQL - WMS` et que les 8 tables apparaissent (VM démarrées). |
| Modèle sémantique `Ventes et logistique` | Paramètres > Informations d'identification de la source : OneLake (Direct Lake) et SharePoint (table `Budget`, OAuth2). Paramètres > Actualisation : désactiver **Maintenir vos données Direct Lake à jour** ; c'est le pipeline de transformation qui recadre le modèle (chapitre 5). |
| Modèle sémantique `Analyse des journaux du site` | Informations d'identification de la source Kusto (OAuth2). |
| Eventstream `Flux - Journaux du site` | Ouvrir, vérifier la source Event Hub (connexion `Event Hub - Journaux du site (fabric-listen)`, groupe de consommateurs `fabric`) et la destination Eventhouse (table `logsweb`, traitement des événements avant ingestion), puis **Publier**. |
| Eventstream `Flux - Événements WMS` | Ouvrir, vérifier la destination (table `wms_events`), **Publier**. Relever l'identifiant de l'Eventstream (URL) et celui de sa source personnalisée `WMSEvent`, pour le simulateur (guide 8). |
| Tableau de bord `Tableau de bord - Journaux du site` | Sa définition est exportée vide par l'intégration Git de Fabric : recréez les vignettes sur la base `AmazingZoneEH` à partir de la fonction `fn_ParseWebLogs()` et du chapitre 8 (volume de requêtes, taux d'erreur, durée des réponses). |
| Alerte `Alerte - Disponibilité du site` | Remplacer le destinataire par votre adresse et réactiver la règle. |
| Fonctions de données utilisateur | Ouvrir chaque élément et **Publier** : la publication installe les bibliothèques et active les points de terminaison. |
| Application d'organisation `Pilotage Amazing Zone` | Non prise en charge par fabric-cicd : créez-la dans l'espace (Nouvel élément > Application d'organisation), ajoutez le rapport `Pilotage des ventes et de la logistique` et trois audiences, `Direction`, `Logistique` et `Finance`, dans cet ordre (chapitre 6). |
| Fabric App `Suivi_retards_expedition` | Facultatif : déployée depuis `apps/retards-expedition` avec la CLI Rayfin (voir son `README.md`). Elle lit le modèle `Ventes et logistique`. |

Lancez enfin une fois la procédure stockée `tech.ingestWMS` dans le Warehouse si vous utilisez le pipeline archivé
« Ingestion - WMS par métadonnées » : elle régénère sa table de configuration `tech.ingestWMS_config`.

```sql
EXEC tech.ingestWMS;
```

## 7.7 Valeurs à reporter

Dans `.env` : `FABRIC_ESPACE_ID` (espace de développement), `AMAZINGZONE_POINT_SQL_FABRIC` (Lakehouse >
point de terminaison SQL > chaîne de connexion SQL, sans `https://`), `WMS_EVENTSTREAM_ID` et
`WMS_EVENTSTREAM_SOURCE_ID`. L'identifiant de la source personnalisée se lit par l'API Fabric :

```bash
curl -s -H "Authorization: Bearer $(az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)" \
  "https://api.fabric.microsoft.com/v1/workspaces/$FABRIC_ESPACE_ID/eventstreams/$WMS_EVENTSTREAM_ID/topology" \
  | python3 -c 'import sys,json; [print(s["id"], s["name"]) for s in json.load(sys.stdin)["sources"]]'
```
