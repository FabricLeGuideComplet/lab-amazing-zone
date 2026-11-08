# 11. Industrialisation : déploiement continu vers le test et la production

Ce guide reprend ce que le chapitre 10 met en place dans le lab : un pipeline Azure DevOps qui déploie les éléments
du dossier `workspaces/amazingzone` avec fabric-cicd, dans un espace d'intégration à chaque fusion sur `main`, puis
dans un espace de test et un espace de production après approbation. Le principal de service s'y connecte par
fédération d'identité de charge de travail : aucun secret n'est stocké dans Azure DevOps. La dernière section décrit
l'essai, fait en parallèle, d'un pipeline de déploiement Fabric et d'un plan de déploiement.

Il se joue après le guide 8 (la chaîne a tourné une fois dans votre espace de développement) ; le guide 10 n'est
pas un prérequis. Il demande une organisation Azure DevOps dans laquelle vous pouvez créer un projet, des
connexions de service et des environnements.

## 11.1 Ce que le dépôt contient

| Fichier | Rôle |
|---|---|
| `azure-pipelines.yml` | Pipeline à trois étapes : `Integration`, puis `Test` et `Prod`, chacune attendant l'approbation de son environnement Azure DevOps. Déclenché par un push sur `main` qui touche `workspaces/amazingzone`, `deploiement` ou `eventhouse` |
| `deploiement/etapes-deploiement.yml` | Étapes communes aux trois environnements : Python 3.12, puis la tâche `AzureCLI@2`, qui ouvre une session Azure CLI au nom du principal de service par la connexion de service `fabric-deploiement` et lance `deployer.py` |
| `deploiement/deployer.py` | Le déploiement lui-même, avec fabric-cicd 1.4.0, en phases ordonnées à la main (section 11.6) |
| `workspaces/amazingzone/parameter.yml` | Remplacements par environnement. Les mêmes entrées valent pour l'environnement `LAB` du guide 7 et pour `INTEGRATION`, `TEST` et `PROD` (clé `_ALL_`), à une exception près : les règles des Activator sont arrêtées en intégration |
| `workspaces/amazingzone/Plan - Base KQL avant Lakehouse.DeploymentPlan` | Plan de déploiement en préversion, essayé au chapitre 10 (section 11.8). fabric-cicd ne prend pas en charge les plans : `deployer.py` l'ignore |
| `eventhouse/amazingzoneeh.kql` | Rejoué en partie après chaque déploiement : tables externes et disponibilité de `wms_evenements` dans OneLake, absentes de la définition Git de la base KQL |

## 11.2 Organisation des espaces

Le chapitre 10 distingue l'espace où l'on développe de ceux où l'on déploie. Votre espace
`AmazingZone - Dev - <prénom>` (guide 7) reste celui où vous travaillez ; le pipeline ne le touche pas. Il déploie
le contenu de la branche `main` dans trois autres espaces, qu'aucune personne ne modifie à la main :

| Environnement | Espace | Déploiement | Variable de l'identifiant |
|---|---|---|---|
| `INTEGRATION` | `AmazingZone - Dev` | À chaque fusion sur `main` | `FABRIC_ESPACE_INTEGRATION_ID` |
| `TEST` | `AmazingZone - Test` | Après approbation, à la suite de l'intégration | `FABRIC_ESPACE_TEST_ID` |
| `PROD` | `AmazingZone - Prod` | Après approbation, à la suite du test | `FABRIC_ESPACE_PROD_ID` |

Tous les éléments ne vont pas partout :

| Éléments | Intégration | Test et production | Pourquoi |
|---|---|---|---|
| Dossier « 9 - Archives », éléments créés par Fabric (lien Dataverse, préparation des Dataflows) | Non | Non | Hors de la plateforme active |
| Eventstream `Flux - Journaux du site` | Non | Non | Il lit l'Event Hub avec le même groupe de consommateurs que votre espace de développement |
| Activator `Alerte - Disponibilité du site` et `Alerte - Activité des entrepôts` | Oui, règles arrêtées | Non | Sur des bases vides, ils alerteraient en boucle |
| Notebook `Contrôle - Tenant settings` | Oui | Non | Le contrôle des tenant settings porte sur le locataire : une seule planification suffit |
| API GraphQL `API_Stock_disponible` | Publiée en dernier, si possible | Idem | Elle expose `api.stock_disponible`, que construit le job dbt : sur un espace neuf, le Warehouse n'est qu'une coquille et la publication échoue tant que la chaîne n'a pas tourné |
| Tout le reste | Oui | Oui | |

Le pipeline déploie des définitions, pas des données. Le lab n'exécute pas la chaîne en test ni en production :
les tables du Warehouse et de la base KQL y restent vides, ce qui suffit pour le chapitre.

Le notebook `Contrôle - Tenant settings` arrive dans l'espace d'intégration avec sa planification hebdomadaire. Il
tourne déjà chaque lundi dans votre espace de développement (guide 10) : retirez l'une des deux planifications.

> **Coût.** Chaque environnement ajoute un Eventhouse `AmazingZoneEH`, qui consomme la capacité dès qu'il est actif
> (requêtes, ingestion, entretien des vues matérialisées) : c'est la ligne la plus lourde des trois espaces. Les
> autres éléments ne consomment qu'à l'exécution. Une fois l'essai terminé, supprimez les espaces de test et de
> production, ou au moins leur Eventhouse ; à défaut, suspendez la capacité en fin de séance (guide 9).

## 11.3 Espaces d'intégration, de test et de production

Pour chacun des trois espaces `AmazingZone - Dev`, `AmazingZone - Test` et `AmazingZone - Prod` :

1. Créez l'espace et affectez-le à la capacité de votre espace de développement.
2. **Gérer l'accès** : ajoutez `dp-equipedata` avec le rôle **Administrateur**. Le principal de service
   `SP-Fabric-AmazingZone`, membre du groupe depuis le guide 1, en hérite ; fabric-cicd exige au moins le rôle
   Membre.
3. Ne reliez pas l'espace à Git. Le pipeline est sa seule source : un espace relié verrait chaque déploiement
   comme une modification à valider, et une mise à jour depuis Git y rapporterait les identifiants de l'auteur,
   que seul fabric-cicd remplace.

Si l'espace d'intégration existe déjà et qu'il est relié à Git (c'était le cas au lab, où `AmazingZone - Dev` était
encore relié, vide, à la branche `main`), détachez-le : Paramètres de l'espace > **Intégration Git** >
**Déconnecter l'espace de travail**.

Facultatif, pour la gouvernance (chapitre 10) : rattachez l'espace de production au domaine `Commerce`
(Paramètres de l'espace > Général > Domaine). Un espace tout juste créé peut ne pas apparaître dans la recherche
de l'écran d'affectation des domaines du portail d'administration ; le paramètre de l'espace, lui, s'applique
immédiatement.

Relevez l'identifiant de chaque espace (dans l'URL : `/groups/<identifiant>/`) pour la section 11.5.

> Pour économiser un Eventhouse, vous pouvez prendre votre espace `AmazingZone - Dev - <prénom>` comme espace
> d'intégration. Ses Activator seront alors arrêtés à chaque déploiement (paramètre `shouldRun` de
> `parameter.yml`) et le pipeline écrasera les modifications que vous y auriez faites sans les valider dans le
> dépôt.

## 11.4 Connexion de service par fédération d'identité de charge de travail

La fédération d'identité de charge de travail évite de stocker le secret du principal de service dans Azure
DevOps : Microsoft Entra ID fait confiance au jeton qu'Azure DevOps émet pour la connexion de service, identifié par
un émetteur et un sujet. Rien n'expire ni ne se renouvelle.

### Dépôt et projet Azure DevOps

Créez un projet, puis importez le dépôt : Repos > **Import a repository**, URL de clonage
`https://github.com/FabricLeGuideComplet/lab-amazing-zone`. Si vous préférez garder votre copie sur GitHub, un
pipeline Azure DevOps peut aussi lire un dépôt GitHub ; le YAML ne change pas.

### Connexion de service (Azure DevOps, première partie)

1. Project settings > **Service connections** > New service connection > **Azure Resource Manager**.
2. Type d'identité : **App registration or managed identity (manual)**, pour le principal de service existant ;
   informations d'identification : **Workload identity federation**. Nom de la connexion : `fabric-deploiement`, celui qu'attend
   `deploiement/etapes-deploiement.yml`.
3. Azure DevOps affiche l'**Issuer** (`https://login.microsoftonline.com/<locataire>/v2.0`) et le **Subject
   identifier** (`/eid1/c/pub/t/…/sc/…/<identifiant de la connexion>`). Copiez-les et laissez la page ouverte.

### Informations d'identification fédérées (Microsoft Entra)

4. Microsoft Entra > Inscriptions d'applications > `SP-Fabric-AmazingZone` > **Certificats et secrets** > onglet
   **Informations d'identification fédérées** > Ajouter des informations d'identification.
5. Scénario : **Autre émetteur** (*Other issuer*). Collez l'émetteur et l'identificateur du sujet relevés à
   l'étape 3, nommez l'entrée `azure-devops-fabric-deploiement`, puis ajoutez. Le portail propose aussi un
   scénario propre à GitHub Actions, qui ne sert pas ici.

### Connexion de service (Azure DevOps, fin)

6. Revenez à la connexion et complétez-la : portée **Subscription**, abonnement du lab (identifiant et nom),
   identifiant du locataire et identifiant d'application (client) de `SP-Fabric-AmazingZone`. Vérifiez, puis
   enregistrez.

La connexion est rattachée à un abonnement Azure, mais le déploiement n'y fait rien : il n'appelle que les API de
Fabric. Le principal de service doit seulement voir l'abonnement, ce que lui donnent en principe les rôles du coffre
de clés qu'il tient de `dp-equipedata` (guide 5). Si la vérification échoue faute d'abonnement accessible,
donnez-lui le rôle **Lecteur** sur le groupe de ressources `RG_AmazingZone`.

Le reste ne change pas : le paramètre de locataire qui autorise les principaux de service à appeler les API Fabric
(guide 1) et le partage des connexions Fabric avec `SP-Fabric-AmazingZone` (guide 7) valent pour le pipeline comme
pour le script du guide 7.

## 11.5 Environnements et pipeline Azure DevOps

### Environnements avec approbation

Pipelines > **Environments** > New environment, sans ressource, une fois pour `AmazingZone - Test` et une fois pour
`AmazingZone - Prod` : ce sont les noms qu'attend `azure-pipelines.yml`. Pour chacun, menu **…** > **Approvals and
checks** > **Approvals** : ajoutez le ou les approbateurs (au lab, l'auteur). Créez-les avant le premier passage :
un environnement absent est créé automatiquement par le pipeline, mais sans approbation.

### Pipeline et variables

Pipelines > New pipeline > dépôt importé > **Existing Azure Pipelines YAML file** > `/azure-pipelines.yml`. Avant
de l'exécuter, ouvrez **Variables** et créez les variables ci-dessous. Une variable de pipeline non secrète devient
une variable d'environnement du même nom pendant l'exécution : `deployer.py` et `parameter.yml` les lisent comme
ils lisent le fichier `.env` sur votre poste.

| Variable | Valeur | Lue par |
|---|---|---|
| `FABRIC_ESPACE_INTEGRATION_ID`, `FABRIC_ESPACE_TEST_ID`, `FABRIC_ESPACE_PROD_ID` | Identifiants des trois espaces (section 11.3) | `deployer.py` |
| `CONNEXION_SHAREPOINT_FINANCE` | Identifiant de la connexion `SharePoint - Finance (SP AmazingZone)` | `deployer.py` (liaison de la table `Budget` du modèle) |
| `CONNEXION_POSTGRESQL_WMS`, `CONNEXION_COPYJOB_SP`, `CONNEXION_PIPELINE_SP`, `CONNEXION_DBT_SP`, `CONNEXION_MODELE_SEMANTIQUE_SP`, `CONNEXION_KEYVAULT_SP`, `CONNEXION_EVENTHUB_JOURNAUX`, `CONNEXION_SQL_NOPCOMMERCE_SP` | Celles de votre `.env` (guide 7) | `parameter.yml` |
| `COFFRE_URI`, `SHAREPOINT_HOTE`, `DESTINATAIRE_ALERTES`, `FABRIC_ESPACE_MIRRORING_ID`, `MIRRORING_AMAZINGDB_ID` | Celles de votre `.env` | `parameter.yml` |
| `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` | Locataire et identifiant d'application du principal de service | `parameter.yml` (notebook `Contrôle - Tenant settings`) |

Toutes sont obligatoires, dans les trois environnements : fabric-cicd refuse un fichier de paramètres dont une
variable `$ENV:` active n'est pas définie. Ne créez pas `AZURE_CLIENT_SECRET` : en son absence, `deployer.py` utilise
la session Azure CLI ouverte par la connexion de service, ce qui est tout l'intérêt de la fédération.

Les connexions, le coffre, le site SharePoint et la base mise en miroir sont communs aux trois environnements,
comme au lab. Si vous voulez des connexions distinctes en production, remplacez la clé `_ALL_` des entrées
concernées de `parameter.yml` par une clé par environnement (`INTEGRATION`, `TEST`, `PROD`, et `LAB` pour le guide
7) : fabric-cicd n'accepte pas `_ALL_` à côté d'une autre clé dans la même entrée.

Le pipeline tourne sur un agent hébergé par Microsoft (`ubuntu-latest`). Au lab, le job parallèle hébergé gratuit
(1 800 minutes par mois) a suffi ; une organisation récente peut devoir en demander l'octroi à Microsoft avant le
premier passage. Azure DevOps avertit que le libellé `ubuntu-latest` passe à Ubuntu 26 à partir du 19 octobre
2026 : épinglez une image précise (`ubuntu-24.04`) si vous tenez à un déploiement reproductible.

### Tester depuis votre poste (facultatif)

Le même script tourne en local avec le secret du principal de service, et `--simulation` affiche les éléments qui
seraient publiés sans rien publier :

```bash
pip install fabric-cicd==1.4.0 azure-identity
set -a; . ./.env; set +a
python deploiement/deployer.py --environnement TEST --simulation
```

## 11.6 Premier passage

Lancez le pipeline (Run pipeline) ou poussez une modification sur `main`. Au premier passage, Azure DevOps demande
d'autoriser le pipeline à utiliser la connexion de service et chacun des deux environnements (**Permit**). Après
l'étape d'intégration, approuvez le test, puis la production.

`deployer.py` déroule, pour chaque environnement :

1. l'Eventhouse `AmazingZoneEH`, sa base KQL et le Warehouse `AmazingZoneWH` d'abord : le raccourci
   `wms.evenements` du Lakehouse pointe vers la base KQL, et les tables externes de la base vers le Warehouse ;
2. les tables externes et la disponibilité de `wms_evenements` dans OneLake, rejouées depuis
   `eventhouse/amazingzoneeh.kql` vers le Warehouse de l'espace cible ;
3. tout le reste sauf les Activator et l'API GraphQL, avec l'Eventstream du WMS privé de sa destination Activator
   (dépendance circulaire), et des Eventstreams créés à l'avance sous un nom provisoire (l'API refuse de créer un
   Eventstream dont le nom contient une espace, mais accepte de le renommer) ;
4. la liaison de la table `Budget` du modèle « Ventes et logistique » à la connexion SharePoint ;
5. en intégration seulement, les Activator, puis l'Eventstream du WMS complet ;
6. l'API GraphQL, dont l'échec est signalé sans arrêter le déploiement.

Le script contourne aussi deux limites rencontrées au lab : il déploie depuis une copie du dossier sans l'ensemble
de requêtes intégré de la base KQL (qui cite la base par son propre identifiant logique et empêche sa création sur
un espace vide), et il tronque à 256 caractères les descriptions d'éléments, que l'API de création refuse au-delà.

Durées mesurées au lab : environ 3 min 30 pour l'intégration, autant pour le test, 5 min 30 pour le premier
déploiement de la production dans un espace vide ; 14 minutes pour le passage complet, approbations comprises.

Vérifiez ensuite, dans l'espace d'intégration, que les règles des deux Activator sont à l'arrêt, et dans les trois
espaces, que les éléments sont rangés dans les mêmes dossiers que dans le dépôt. Le message « API GraphQL non
publiée » est attendu sur un espace neuf.

## 11.7 Faire évoluer la plateforme

Toute modification fusionnée sur `main` dans `workspaces/amazingzone`, `deploiement` ou `eventhouse` déclenche le
pipeline. Un message de commit qui contient `[skip ci]` ne le déclenche pas ; le lab s'en sert pour valider des
éléments qui ne se déploient pas, comme le plan de la section 11.8.

`parameter.yml` remplace les identifiants de l'environnement de l'auteur, ceux qui figurent dans le dépôt. Si
vous faites évoluer les éléments depuis un espace relié à Git, les fichiers que vous validerez porteront les
identifiants de votre espace de développement : remplacez alors les `find_value` correspondants de
`parameter.yml` (espace, Lakehouse, Warehouse, point de terminaison SQL, modèle sémantique, base KQL, URI de
l'Eventhouse, tableau de bord, Eventstream) par les vôtres.

## 11.8 Pipeline et plans de déploiement de Fabric

Le chapitre 10 compare fabric-cicd aux outils intégrés à Fabric. Ce qui suit décrit l'essai du lab ; rien n'est
nécessaire au déploiement continu des sections précédentes.

### Pipeline de déploiement

Le lab a créé un pipeline de déploiement Fabric, « AmazingZone - Essai pipeline de déploiement », à deux étapes :
Développement (`AmazingZone - Dev`) et Test (`AmazingZone - Test`). À l'affectation des espaces, Fabric a apparié
les éléments de même nom et de même type, sans créer de doublon, bien qu'ils aient été créés par fabric-cicd. Le
déploiement sélectif du seul « Tableau de bord - Suivi des entrepôts » de Dev vers Test a rebranché sa source sur
la base KQL appariée de l'étape cible, ce que fabric-cicd obtient par une entrée de `parameter.yml`. En revanche,
après le déploiement d'« Orchestration - Transformation », l'activité d'actualisation du modèle sémantique
pointait encore vers le modèle de l'espace de développement : le rebranchement n'est que partiel.

Un pipeline créé par le principal de service n'est visible que de lui : ajoutez `dp-equipedata` comme
administrateur du pipeline pour l'ouvrir depuis l'interface.

### Plan « Plan - Base KQL avant Lakehouse »

Les plans de déploiement sont en préversion à l'automne 2026. Ils s'activent par le tenant setting **Users can
create deployment plan (preview) items**, que le lab réserve au groupe `dp-equipedata` (référence
`gouvernance/tenant-settings-reference.json`). Un plan fixe l'ordre de déploiement des éléments (un groupe par
élément, avec ses dépendances) et peut exécuter des actions avant ou après un groupe (notebook, pipeline,
Dataflow, Copy Job, fonction de données).

Le plan du dépôt ordonne la base KQL `AmazingZoneEH` avant le Lakehouse `AmazingZoneLK`, l'ordre que `deployer.py`
impose à la main :

```yaml
groups:
  - name: AmazingZoneEH_KustoDatabase
    logicalId: 16141940-050c-9467-467e-3ee59afe9a4e
  - name: AmazingZoneLK_Lakehouse
    logicalId: 8d1ef2af-cebe-a672-401b-e450f6523eec
    dependsOn:
      - groupName: AmazingZoneEH_KustoDatabase
```

Ses identifiants sont les identifiants logiques des fichiers `.platform` du dépôt : il a été conçu dans un espace
relié à Git. Un espace déployé par fabric-cicd, comme le vôtre au guide 7, a d'autres identifiants logiques ; pour
y essayer un plan, créez-le dans l'interface (Nouvel élément > **Deployment Plan (preview)**), puis glissez les
éléments sur le canevas et tracez la dépendance. Un nom de plan accentué est refusé.

Ce que l'essai a montré :

- depuis l'interface, le déploiement avec plan fonctionne. Dans le pipeline de déploiement, sélectionnez les
  éléments différents de la source ou nouveaux, choisissez un plan de la source dans la liste **with plan**, puis
  confirmez dans la boîte **Deploy with plan** ; une action ne s'exécute que si l'élément de son groupe fait partie
  du déploiement ;
- par l'API (Deploy Stage Content avec plan, en bêta) et sous le principal de service, l'exécution d'un plan
  renvoyait une erreur 500 (*InternalServerError*) au 7 novembre 2026, alors que la création du plan par l'API
  réussissait ;
- avec Git, **Branch out with deployment plan** (volet Source control) a créé l'espace de branche dans l'ordre du
  plan, raccourci `wms.evenements` compris ; ce raccourci restait pourtant en erreur, car la disponibilité de la
  table dans OneLake ne voyage pas par Git : le plan règle l'ordre, pas ce que Git ne porte pas.

fabric-cicd ne prend pas en charge les plans de déploiement : `deployer.py` garde son ordre imposé à la main.
