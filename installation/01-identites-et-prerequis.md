# 1. Identités et prérequis

Ce guide prépare ce dont toutes les étapes suivantes dépendent : les licences, les comptes, le groupe de
l'équipe Data, le principal de service du lab et les outils à installer sur votre poste.

## 1.1 Licences et abonnements

| Besoin | Usage dans le lab | Remarque |
|---|---|---|
| Un locataire Microsoft Entra ID dont vous êtes administrateur | Paramètres du locataire Fabric, consentement administrateur, groupes | Un locataire de développement Microsoft 365 ou un locataire d'essai convient. |
| Un abonnement Azure | Site e-commerce, WMS, Event Hubs, Key Vault | Rôle Propriétaire sur l'abonnement (ou au moins sur les groupes de ressources) pour attribuer des rôles. |
| Une capacité Fabric | Tous les éléments Fabric | Capacité d'évaluation (Trial) si elle est disponible, sinon une F2 au minimum, à suspendre en dehors des séances. |
| Une licence Power BI Pro ou Premium par utilisateur | Partage des rapports et de l'application d'organisation | Incluse dans la capacité d'évaluation pour les comptes qui l'activent. |
| SharePoint Online | Référentiels Excel (guide 4) | Inclus dans Microsoft 365. |
| Dynamics 365 Customer Service (essai) | Lien Fabric Dataverse (guide 6) | Facultatif, essai de 30 jours. |

Si votre propre attribution de rôle Propriétaire porte une condition (contrôle d'accès basé sur les attributs),
certaines opérations échouent avec `InsufficientPermissions`, en particulier le passage du coffre de clés en
RBAC (guide 5). Utilisez alors un compte dont l'attribution n'a pas de condition.

## 1.2 Groupe de l'équipe Data

Le lab attribue les droits à un groupe plutôt qu'à des personnes : le groupe `dp-equipedata` est administrateur
Microsoft Entra du serveur Azure SQL, administrateur du domaine Fabric « Commerce », membre des espaces de
travail et titulaire des rôles du coffre de clés.

1. Centre d'administration Microsoft Entra > Groupes > Nouveau groupe : type **Sécurité**, nom `dp-equipedata`.
2. Ajoutez-y votre compte, puis, une fois créé (section 1.3), le principal de service `SP-Fabric-AmazingZone`.

```bash
az ad group create --display-name dp-equipedata --mail-nickname dp-equipedata
GROUPE_ID=$(az ad group show --group dp-equipedata --query id -o tsv)
az ad group member add --group dp-equipedata --member-id $(az ad signed-in-user show --query id -o tsv)
```

## 1.3 Principal de service du lab

Les scripts du dépôt, le déploiement des éléments et plusieurs connexions Fabric s'authentifient avec un
principal de service dédié, `SP-Fabric-AmazingZone`. Le livre défend ce choix au chapitre 4 : une connexion
portée par un compte personnel cesse de fonctionner le jour où ce compte change de mot de passe ou quitte
l'entreprise.

1. Microsoft Entra > Inscriptions d'applications > Nouvelle inscription : nom `SP-Fabric-AmazingZone`, comptes de
   cet annuaire uniquement, sans URI de redirection.
2. Certificats et secrets > Nouveau secret client : durée 6 ou 12 mois. Copiez la valeur immédiatement : elle
   n'est plus affichable ensuite. Elle sert aux scripts du dépôt et au déploiement.
3. Notez l'**ID d'application (client)**, l'**ID de l'annuaire (locataire)** et l'**ID d'objet** de l'application
   d'entreprise (Microsoft Entra > Applications d'entreprise > `SP-Fabric-AmazingZone`). C'est ce dernier qu'on
   ajoute aux espaces de travail et aux groupes.
4. Ajoutez le principal de service au groupe `dp-equipedata`.

```bash
APP_ID=$(az ad app create --display-name SP-Fabric-AmazingZone --query appId -o tsv)
SP_ID=$(az ad sp create --id $APP_ID --query id -o tsv)
az ad app credential reset --id $APP_ID --display-name lab --years 1   # affiche le secret une seule fois
az ad group member add --group dp-equipedata --member-id $SP_ID
```

Le certificat qui permet au principal de service de lire SharePoint est créé dans le coffre de clés (guide 5) ;
un secret client ne suffit pas pour SharePoint, qui refuse les jetons d'application obtenus par secret.

Recopiez `.env.exemple` en `.env` à la racine du dépôt et renseignez `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` et
`AZURE_CLIENT_SECRET`. Le fichier `.env` est exclu du dépôt par `.gitignore`.

## 1.4 Paramètres du locataire Fabric

Portail Fabric > Paramètres > Portail d'administration > Paramètres du locataire. Activez au minimum, de
préférence pour le groupe `dp-equipedata` plutôt que pour toute l'organisation :

| Section | Paramètre | Pourquoi |
|---|---|---|
| Paramètres des développeurs | Les principaux de service peuvent appeler les API publiques Fabric | Déploiement par fabric-cicd, scripts du dépôt, simulateur temps réel |
| Paramètres des développeurs | Les principaux de service peuvent créer des espaces de travail, des connexions et des pipelines de déploiement | Création de connexions par API (facultatif) |
| Intégration Git | Les utilisateurs peuvent synchroniser les éléments de l'espace avec leurs dépôts Git (et, pour GitHub, le paramètre propre à GitHub) | Synchronisation de l'espace de développement |
| Paramètres Microsoft Fabric | Les utilisateurs peuvent créer des éléments Fabric | Tous les éléments |
| Paramètres Microsoft Fabric | Fonctionnalités en préversion utilisées par le livre : job dbt, vues matérialisées de lac (MLV), fonctions de données utilisateur, applications d'organisation, Fabric Apps | Chapitres 5 et 6 |
| Paramètres d'administration | Récupération des éléments supprimés (corbeille) | Filet de sécurité décrit au chapitre 10 |

Les intitulés évoluent d'une version du portail à l'autre ; cherchez-les par mot-clé dans la page.

## 1.5 Outils sur votre poste

| Outil | Version utilisée | Usage |
|---|---|---|
| Azure CLI (`az`) | 2.6x | Création des ressources Azure (les guides donnent les commandes ; le portail convient aussi) |
| Python | 3.11 ou plus | Générateurs de données, simulateur, déploiement |
| Pilote ODBC 18 pour SQL Server | 18.x | Générateurs de données (`pyodbc`) |
| Paquets Python | `pyodbc`, `openpyxl`, `azure-eventhub`, `fabric-cicd`, `azure-identity` | `pip install pyodbc openpyxl azure-eventhub fabric-cicd azure-identity` |
| Client SSH | | Administration de la VM PostgreSQL |
| Client Bureau à distance | | Installation de la passerelle sur la VM Windows |
| Node.js 20 ou plus | | Fabric App (facultatif, chapitre 6) |
| Visual Studio Code et dbt Core (adaptateur `dbt-fabric`) | | Développement local du projet dbt (facultatif) |

Les commandes `az` des guides supposent une session ouverte avec votre compte (`az login`) et l'abonnement du
lab sélectionné (`az account set --subscription <id>`).

Si votre Azure CLI sert déjà à un autre locataire, celui d'un client par exemple, isolez la session du lab dans
son propre dossier de configuration plutôt que de basculer d'un locataire à l'autre :

```bash
export AZURE_CONFIG_DIR=~/.azure-lab-amazingzone      # à exporter dans chaque terminal du lab
az login --tenant <ID du locataire du lab>            # --use-device-code si le navigateur est sur une autre machine
```

Vos autres sessions `az` restent intactes.
