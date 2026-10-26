# 6. Dynamics 365 Customer Service et Dataverse (facultatif)

Le service client d'Amazing Zone travaille dans Dynamics 365 Customer Service. Le chapitre 4 relie ses données
Dataverse à Fabric par un lien Fabric (Link to Microsoft Fabric), qui expose les tables sous forme de raccourcis
dans un Lakehouse géré par Dataverse. Cette étape est facultative : aucun autre élément du lab n'en dépend.

| Élément | Lab de l'auteur |
|---|---|
| Environnement | Essai « CustomerService Trial », région France, langue de base français, données d'exemple de Microsoft |
| Lien Fabric | Mode faible latence, vers l'espace « AmazingZone - Dev - <prénom> » |
| Authentification | Identité de l'espace de travail, déclarée comme utilisateur d'application Dataverse avec le rôle Administrateur système |
| Connexion | « Dataverse - CustomerService » |
| Tables | `account`, `contact`, `incident`, `email`, `phonecall`, `knowledgearticle` |

## 6.1 Environnement d'essai

1. Depuis la page de Dynamics 365 Customer Service, démarrez un essai gratuit avec un compte du locataire du lab.
2. Choisissez la région **France** et le français comme langue de base, et acceptez les données d'exemple.
3. Notez l'URL de l'organisation (`https://<org>.crm12.dynamics.com`) dans le centre d'administration Power Platform.

L'essai dure 30 jours et se prolonge une fois depuis le centre d'administration Power Platform.

## 6.2 Prérequis du lien Fabric

- La capacité Fabric de l'espace cible doit se trouver dans la même zone géographique que l'environnement
  Dataverse (France).
- L'identité de l'espace de travail doit exister (guide 7, section 7.2). Dans le centre d'administration Power
  Platform > environnement > Paramètres > Utilisateurs et autorisations > **Utilisateurs d'application** >
  Nouvel utilisateur d'application : choisissez l'application qui porte le nom de l'espace, la division racine et le
  rôle de sécurité **Administrateur système**. Le chapitre 4 discute ce niveau de droits, exigé par le lien.

## 6.3 Créer le lien

1. Power Apps (make.powerapps.com) > environnement Customer Service > **Analyse** > **Azure Synapse Link** >
   **Lier à Microsoft Fabric**.
2. Choisissez l'espace « AmazingZone - Dev - <prénom> » et l'identité de l'espace de travail comme
   authentification (connexion « Dataverse - CustomerService »).
3. Sélectionnez les six tables du tableau ci-dessus, puis validez. La première synchronisation prend de quelques
   minutes à une heure.

Dataverse crée dans l'espace un Lakehouse nommé `dataverse_<environnement>_cds2_workspace_unq<identifiant>`, avec
un raccourci par table et son point de terminaison SQL. Ce Lakehouse est géré par le lien : ne le synchronisez
pas avec Git et ne le modifiez pas, il serait recréé ou désynchronisé au prochain changement du lien.
