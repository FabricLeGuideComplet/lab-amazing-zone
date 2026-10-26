# 2. Site e-commerce nopCommerce

Le site d'Amazing Zone est une boutique nopCommerce hébergée dans Azure App Service, adossée à une base Azure
SQL Database. Il alimente deux flux de la plateforme : la base est répliquée dans Fabric par le mirroring
(chapitre 4), et les journaux de diagnostic de l'App Service partent vers un Event Hub que lit un Eventstream
(chapitres 4 et 8).

Configuration du lab de l'auteur, que les commandes ci-dessous reproduisent :

| Ressource | Nom dans le lab | Configuration |
|---|---|---|
| Groupe de ressources | `RG_AmazingZone` | France Central |
| Serveur logique Azure SQL | `amazingserver` | Identité managée affectée par le système, administrateur Entra = groupe `dp-equipedata`, authentification SQL conservée (`sqladmin`) pour nopCommerce, TLS 1.2 minimum, accès public |
| Base | `amazingdb` | General Purpose serverless, Gen5, 1 vCore maximum, 0,5 vCore minimum, pause automatique après 60 minutes, classement `SQL_Latin1_General_CP1_CI_AS`, sauvegardes en stockage local (LRS) |
| Plan App Service | `ASP-RGAmazingZone-9d6a` | Windows, Basic B1, une instance |
| Application web | `AmazingWeb` | Windows, pile .NET 10 (LTS), 64 bits, HTTPS uniquement, FTPS uniquement, Always On désactivé |
| Application | nopCommerce 4.90 (paquet `NoSource_win_x64`, autonome : il embarque .NET 9) | Déployé par ZipDeploy, installé avec les données d'exemple, anglais et français |
| Application Insights | `AmazingWeb` | Mode basé sur un espace de travail Log Analytics |
| Espace de noms Event Hubs | `WebLogsAZ` | Standard, 1 unité de débit, pas d'auto-inflate |
| Event Hub | `weblogs` | 1 partition, rétention 1 heure, groupes de consommateurs `$Default` et `fabric`, stratégie `fabric-listen` (Listen) |
| Paramètre de diagnostic | `Logs` sur `AmazingWeb` | Toutes les catégories de journaux et `AllMetrics` vers `weblogs` |

Les noms de serveur SQL, d'application web, d'espace de noms Event Hubs et de coffre de clés sont uniques dans
Azure : choisissez les vôtres et reportez-les dans `.env`.

```bash
RG=RG_AmazingZone
REGION=francecentral
SQL_SERVEUR=amazingserver-<suffixe>       # nom unique
SQL_ADMIN=sqladmin
SQL_MDP='<mot de passe fort>'             # ne le versionnez pas
SITE=amazingweb-<suffixe>                 # nom unique
EH_NS=weblogsaz-<suffixe>                 # nom unique
GROUPE_ID=$(az ad group show --group dp-equipedata --query id -o tsv)

az group create -n $RG -l $REGION
```

## 2.1 Base Azure SQL Database

```bash
# Serveur logique, avec l'identité managée exigée par le mirroring Fabric
az sql server create -g $RG -n $SQL_SERVEUR -l $REGION \
   --admin-user $SQL_ADMIN --admin-password "$SQL_MDP" \
   --assign-identity --minimal-tls-version 1.2

# Administrateur Microsoft Entra : le groupe de l'équipe Data
az sql server ad-admin create -g $RG -s $SQL_SERVEUR \
   --display-name dp-equipedata --object-id $GROUPE_ID

# Pare-feu : services Azure (nécessaire au mirroring et à l'App Service) et votre adresse IP
az sql server firewall-rule create -g $RG -s $SQL_SERVEUR -n AllowAllWindowsAzureIps \
   --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
MON_IP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create -g $RG -s $SQL_SERVEUR -n poste-admin \
   --start-ip-address $MON_IP --end-ip-address $MON_IP

# Base serverless
az sql db create -g $RG -s $SQL_SERVEUR -n amazingdb \
   --edition GeneralPurpose --family Gen5 --capacity 1 \
   --compute-model Serverless --min-capacity 0.5 --auto-pause-delay 60 \
   --collation SQL_Latin1_General_CP1_CI_AS --backup-storage-redundancy Local
```

Le lab de l'auteur ouvre le pare-feu à toutes les adresses par commodité. Les deux règles ci-dessus suffisent :
l'App Service et Fabric passent par la règle des services Azure, vos scripts par la règle de votre poste.

La base créée vide, nopCommerce y crée son schéma pendant l'installation (section 2.3). Une base serverless en
pause met environ une minute à reprendre : la première connexion après une pause peut échouer avec l'erreur
40613 (*Database is not currently available*). Il suffit de réessayer.

## 2.2 App Service

```bash
az appservice plan create -g $RG -n ASP-AmazingZone -l $REGION --sku B1 --is-linux false
az webapp create -g $RG -p ASP-AmazingZone -n $SITE --runtime "dotnet:10"
az webapp update -g $RG -n $SITE --https-only true
az webapp config set -g $RG -n $SITE --ftps-state FtpsOnly \
   --use-32bit-worker-process false --always-on false
```

Sans `--is-linux false`, les versions récentes d'Azure CLI créent un plan Linux, et la création de l'application
échoue ensuite avec *Linux Runtime 'dotnet|10' is not supported*. Supprimez alors le plan et recréez-le.

Le choix de la pile importe peu : le paquet `NoSource_win_x64` de nopCommerce est autonome (*self-contained*), il
embarque son propre runtime .NET 9 (`coreclr.dll`, `hostfxr.dll`) et ne dépend pas de celui de l'App Service. Le lab
déclare la pile .NET 10, version LTS, parce que la pile .NET 9 d'App Service arrive en fin de support le
10 novembre 2026 ; le site a été vérifié ainsi le 26 octobre 2026.

Always On reste désactivé pour limiter la consommation ; le premier appel après une période d'inactivité prend
alors jusqu'à une minute, le temps de démarrer l'application et, le cas échéant, de réveiller la base.

## 2.3 Déploiement et installation de nopCommerce

### Télécharger le paquet

Les versions publiées sont sur <https://github.com/nopSolutions/nopCommerce/releases>. Le lab a été installé
avec nopCommerce 4.90.4 (mars 2026) ; toute version 4.90.x convient. Prenez le paquet **sans sources** pour
Windows 64 bits, `nopCommerce_4.90.x_NoSource_win_x64.zip` : il contient l'application compilée, prête à
exécuter, sans Visual Studio ni SDK .NET.

```bash
VERSION=4.90.4
curl -LO https://github.com/nopSolutions/nopCommerce/releases/download/release-$VERSION/nopCommerce_${VERSION}_NoSource_win_x64.zip
unzip -l nopCommerce_${VERSION}_NoSource_win_x64.zip | grep -E " Nop.Web.(dll|exe)$"   # les fichiers doivent être à la racine
```

Si `Nop.Web.dll` se trouve dans un sous-dossier de l'archive, décompressez-la et recompressez le contenu de ce
sous-dossier : ZipDeploy copie l'archive telle quelle dans `site\wwwroot`.

### Déployer

```bash
az webapp deploy -g $RG -n $SITE --src-path nopCommerce_${VERSION}_NoSource_win_x64.zip --type zip
```

Le transfert de l'archive (140 Mo) puis son déploiement durent cinq à sept minutes sur un plan B1. Il arrive que la
commande s'arrête au bout de cinq minutes avec *Status Code: 504* : c'est le délai d'attente de la commande qui
expire, pas le déploiement, qui se poursuit côté Azure. Suivez-le jusqu'au statut 4 (réussi) avant d'aller plus loin :

```bash
az webapp log deployment list -g $RG -n $SITE --query "[0].{statut:status, fin:end_time}"
```

Le premier appel du site après le déploiement peut répondre 502 ou 503 pendant une minute, le temps du démarrage.
Ouvrez ensuite `https://<site>.azurewebsites.net/` : nopCommerce
redirige vers son assistant d'installation (`/install`).

### Assistant d'installation

| Champ | Valeur du lab |
|---|---|
| Admin user email | Une adresse à vous, qui servira d'identifiant d'administration de la boutique |
| Admin user password / Confirm password | Un mot de passe fort, à ranger dans votre gestionnaire de mots de passe |
| Country | France : l'assistant télécharge le pack de langue français, en plus de l'anglais |
| Create sample data | **Coché** : catalogue de démonstration (47 produits, 16 catégories), six comptes clients et quelques commandes, sur lesquels s'appuient les générateurs de données du dépôt |
| Database | Microsoft SQL Server |
| Create database if it doesn't exist | Décoché : la base existe déjà |
| Enter raw connection string (advanced) | Décoché |
| Server name | `<serveur>.database.windows.net` |
| Database name | `amazingdb` |
| Use integrated Windows authentication | Décoché |
| SQL Username / SQL Password | `sqladmin` et son mot de passe |
| Collation | Laisser vide (le classement de la base s'applique) |

Cliquez sur **Install**. La création du schéma et des données d'exemple prend quatre minutes environ, davantage si la
base sortait de pause. L'application redémarre ensuite d'elle-même et affiche la boutique.

L'App Service coupe toute requête au bout de 230 secondes : il arrive que l'assistant réaffiche son formulaire, sans
message d'erreur, alors que l'installation s'est bien terminée côté serveur. Avant de relancer quoi que ce soit,
regardez la base : si `dbo.Product` contient 47 produits et que le fichier `App_Data/plugins.json` existe sur le
site, l'installation est faite et il ne manque que le redémarrage. Lancez-le vous-même :

```bash
az webapp restart -g $RG -n $SITE
```

La boutique s'affiche une à deux minutes plus tard.

Le jeu d'exemple garde le dollar américain comme devise principale (l'euro est publié comme seconde devise) et
le nom de boutique par défaut, « Your store name ». Le lab n'en change rien : les générateurs et le projet dbt
en tiennent compte.

La chaîne de connexion est enregistrée par nopCommerce dans `App_Data/appsettings.json`, en clair, sur
l'App Service. C'est le fonctionnement standard de l'application ; le chapitre 9 du livre revient sur ce type
de secret.

### Vérifier

- La boutique s'affiche avec le catalogue d'exemple (cartes cadeaux, ordinateurs, vêtements, logiciels).
- `https://<site>.azurewebsites.net/admin` accepte le compte d'administration.

Si vous vérifiez le site par script (`curl`, `requests`), donnez à vos requêtes l'en-tête `User-Agent` d'un
navigateur : nopCommerce traite les clients HTTP qu'il ne reconnaît pas comme des robots d'indexation et leur sert
le compte invité réservé aux moteurs de recherche. La connexion est alors acceptée, puis aussitôt oubliée, et
`/admin` renvoie indéfiniment vers la page de connexion.
- Dans la base, la requête suivante renvoie 47 produits et 16 catégories :

```sql
SELECT (SELECT COUNT(*) FROM dbo.Product WHERE Deleted = 0) AS produits,
       (SELECT COUNT(*) FROM dbo.Category) AS categories,
       (SELECT COUNT(*) FROM dbo.[Order]) AS commandes;
```

## 2.4 Accès du principal de service à la base

Les générateurs de données (`ecommerce/donnees_demo`, `wms/donnees_demo`) se connectent avec le principal de
service, qui doit être `db_owner` de `amazingdb`. Connectez-vous à la base avec un compte membre de
`dp-equipedata` (éditeur de requêtes du portail Azure, SSMS ou l'extension SQL de VS Code), puis :

```sql
CREATE USER [SP-Fabric-AmazingZone] FROM EXTERNAL PROVIDER;
ALTER ROLE db_owner ADD MEMBER [SP-Fabric-AmazingZone];
```

Exécutée depuis un compte utilisateur Microsoft Entra, cette commande a fonctionné lors du rejeu de l'installation
(octobre 2026) sans que l'identité du serveur SQL ait le rôle Microsoft Entra *Directory Readers*. Si elle échoue
parce que le principal est introuvable, ou si vous l'exécutez avec un principal de service, ce rôle devient
nécessaire. À défaut, créez l'utilisateur à partir de l'ID d'application :

```sql
DECLARE @sid NVARCHAR(100) = CONVERT(NVARCHAR(100),
        CONVERT(VARBINARY(16), CAST('<ID d''application du principal de service>' AS UNIQUEIDENTIFIER)), 1);
EXEC ('CREATE USER [SP-Fabric-AmazingZone] WITH SID = ' + @sid + ', TYPE = E');
ALTER ROLE db_owner ADD MEMBER [SP-Fabric-AmazingZone];
```

L'utilisateur de l'identité de l'espace « AmazingZone - Mirroring », qui porte le mirroring, se crée de la même
façon au guide 7.

## 2.5 Application Insights

Portail Azure > application web > **Application Insights** > Activer : créer une ressource `AmazingWeb` dans
la même région, en mode basé sur un espace de travail Log Analytics, avec l'instrumentation automatique .NET
recommandée. Le livre la présente au chapitre 2 ; la plateforme de données n'en consomme pas les données.

Le même résultat en ligne de commande (l'extension `application-insights` d'Azure CLI s'installe à la première
utilisation) :

```bash
az monitor log-analytics workspace create -g $RG -n law-amazingweb -l $REGION
az monitor app-insights component create -g $RG -a AmazingWeb -l $REGION --kind web --application-type web \
   --workspace $(az monitor log-analytics workspace show -g $RG -n law-amazingweb --query id -o tsv)
az webapp config appsettings set -g $RG -n $SITE --settings \
   APPLICATIONINSIGHTS_CONNECTION_STRING="$(az monitor app-insights component show -g $RG -a AmazingWeb --query connectionString -o tsv)" \
   ApplicationInsightsAgent_EXTENSION_VERSION="~2" XDT_MicrosoftApplicationInsights_Mode=recommended
```

## 2.6 Journaux de diagnostic vers Event Hubs

```bash
az eventhubs namespace create -g $RG -n $EH_NS -l $REGION --sku Standard --capacity 1
az eventhubs eventhub create -g $RG --namespace-name $EH_NS -n weblogs \
   --partition-count 1 --cleanup-policy Delete --retention-time-in-hours 1

# Groupe de consommateurs et stratégie en lecture seule réservés à Fabric (chapitre 4)
az eventhubs eventhub consumer-group create -g $RG --namespace-name $EH_NS --eventhub-name weblogs -n fabric
az eventhubs eventhub authorization-rule create -g $RG --namespace-name $EH_NS --eventhub-name weblogs \
   -n fabric-listen --rights Listen

# Paramètre de diagnostic de l'App Service : toutes les catégories et les métriques vers weblogs
REGLE=$(az eventhubs namespace authorization-rule show -g $RG --namespace-name $EH_NS \
        -n RootManageSharedAccessKey --query id -o tsv)
az monitor diagnostic-settings create -n Logs \
   --resource $(az webapp show -g $RG -n $SITE --query id -o tsv) \
   --event-hub weblogs --event-hub-rule $REGLE \
   --logs '[{"categoryGroup":"allLogs","enabled":true}]' \
   --metrics '[{"category":"AllMetrics","enabled":true}]'
```

Le paramètre de diagnostic exige une règle d'autorisation au niveau de l'espace de noms, avec les droits
Manage, Send et Listen ; la règle par défaut `RootManageSharedAccessKey` les a. Fabric, lui, ne lit qu'avec
`fabric-listen` et le groupe `fabric`, pour ne pas partager le curseur de lecture du groupe `$Default`.

Seules les catégories `AppServiceHTTPLogs` et `AppServiceAppLogs` sont exploitées par la fonction KQL
`fn_ParseWebLogs` ; les autres restent disponibles pour l'exploration.

Pour vérifier le flux : naviguez quelques minutes sur la boutique, puis ouvrez l'Event Hub `weblogs` dans le
portail Azure > **Data Explorer** > View events. Les premiers enregistrements arrivent après deux à cinq
minutes, par lots.

Le contrôle peut aussi se faire avec les droits exacts qu'aura Fabric, la stratégie `fabric-listen` et le groupe
`fabric` : le script ci-dessous lit pendant 40 secondes et compte les enregistrements par catégorie.

```bash
export EH_CS=$(az eventhubs eventhub authorization-rule keys list -g $RG --namespace-name $EH_NS \
   --eventhub-name weblogs --authorization-rule-name fabric-listen --query primaryConnectionString -o tsv)
python - <<'FIN'
import collections, json, os, threading, time
from azure.eventhub import EventHubConsumerClient
client = EventHubConsumerClient.from_connection_string(os.environ["EH_CS"], consumer_group="fabric")
categories = collections.Counter()
def lire(partition, evenement):
    for r in json.loads(evenement.body_as_str()).get("records", []):
        categories[r.get("category") or r.get("metricName")] += 1
threading.Thread(target=lambda: (time.sleep(40), client.close())).start()
client.receive(on_event=lire, starting_position="-1")
print(dict(categories.most_common(6)))   # AppServiceAppLogs, AppServiceHTTPLogs, métriques…
FIN
```

## 2.7 Valeurs à reporter

Dans `.env` :

```bash
AMAZINGZONE_SQL_SERVEUR=<serveur>.database.windows.net
AMAZINGZONE_SQL_BASE=amazingdb
```

Les données de démonstration (600 clients et environ 4 000 commandes) se génèrent au guide 8. Le générateur
répartit les clients sur les départements du référentiel géographique, qu'il lit dans la copie versionnée
`referentiels/referentiel_geographique.xlsx` : il ne dépend pas de Fabric et peut tourner dès que le site est
installé.
