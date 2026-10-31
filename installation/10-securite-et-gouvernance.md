# 10. Sécurité des données et contrôle des tenant settings

Ce guide reprend ce que le chapitre 9 met en place dans le lab et que le dépôt contient : la sécurité au niveau des
lignes et des colonnes, appliquée à la fois dans le Warehouse et dans le modèle sémantique « Ventes et logistique »,
puis le contrôle hebdomadaire des tenant settings. Il se joue après la première exécution réussie du guide 8.

## 10.1 Ce que le dépôt contient

| Élément | Contenu |
|---|---|
| Seed `securite_entrepot` (job dbt) | Le périmètre de chaque utilisateur : son UPN et les codes des entrepôts qu'il a le droit de voir. C'est la seule source des deux sécurités au niveau des lignes. Vous l'avez renseigné avant le déploiement (guide 7, section 7.5) |
| Modèle dbt `securite.AccesEntrepot` | Le seed joint à `gold.DimEntrepot`, avec une ligne par utilisateur et par entrepôt autorisé |
| `macros/securite.sql` et hooks de `dbt_project.yml` | En début d'exécution, retrait de la politique `securite.politique_entrepot` et de sa fonction. En fin d'exécution, elles sont recréées avec les rôles `lecteurs_gold` (lecture du Gold sans `DimClient.Email`) et `acces_tous_entrepots` (variable `securite_acces_complet` : le principal de service et `dp-equipedata`) |
| Rôle « Lecteurs par entrepôt » du modèle | Filtre dynamique sur `Entrepôt` par `USERPRINCIPALNAME()`, qui se propage aux ventes, aux expéditions, au stock et à la météo ; colonne `Client[Email]` masquée (sécurité au niveau des objets) |
| Notebook `Contrôle - Tenant settings` et `gouvernance/tenant-settings-reference.json` | La référence des tenant settings attendus et le notebook qui la compare chaque semaine à l'état réel du locataire |

La politique est liée au schéma (`SCHEMABINDING`) et interdit de renommer ou de supprimer les tables qu'elle
protège : c'est pourquoi dbt la retire avant de reconstruire les tables. Pendant une exécution du job, la sécurité
est donc levée : les faits ne sont pas filtrés, et la colonne `Email` est lisible par `lecteurs_gold`. Si une
instruction de fin d'exécution échoue, la sécurité n'est rétablie qu'à la prochaine exécution réussie. Le
chapitre 9 discute ce compromis.

## 10.2 Sécurité du Warehouse

Rien à faire de plus si le seed contient des UPN valides : la première transformation du guide 8 a créé les
utilisateurs dans le Warehouse (création implicite à l'ajout au rôle), la table de correspondance, la politique et
les rôles. Deux points d'entretien :

- un utilisateur retiré du seed reste membre de `lecteurs_gold` : retirez-le à la main
  (`ALTER ROLE lecteurs_gold DROP MEMBER [upn]`) ;
- si vous renommez le principal de service ou le groupe de l'équipe Data, adaptez la variable
  `securite_acces_complet` de `dbt_project.yml`. Un administrateur de l'espace n'échappe pas à la sécurité T-SQL :
  sans ce rôle, il ne voit aucune ligne des faits.

Pour vérifier en lecteur, partagez le Warehouse avec un utilisateur du seed sans cocher aucune case (connexion
seule), puis connectez-vous avec son compte. `EXECUTE AS USER` n'est pas pris en charge dans le Warehouse
(erreur 15868) : le test demande une vraie connexion sous son identité.

```sql
SELECT USER_NAME();                                   -- son UPN
SELECT e.CodeEntrepot, COUNT(*) AS lignes             -- seuls ses entrepôts
FROM gold.FaitVente AS f JOIN gold.DimEntrepot AS e ON e.EntrepotKey = f.EntrepotKey
GROUP BY e.CodeEntrepot;
SELECT TOP 5 Email FROM gold.DimClient;               -- refusé : SELECT permission was denied on the column
SELECT TOP 5 ClientKey FROM gold.DimClient;           -- autorisé
SELECT * FROM securite.AccesEntrepot;                 -- refusé : aucun droit sur le schéma securite
```

## 10.3 Sécurité du modèle sémantique

Le modèle « Ventes et logistique » lit le Warehouse en Direct Lake. Avec l'authentification unique (SSO), le
filtre du rôle s'appliquerait sur l'identité de chaque lecteur, mais Fabric déconseille d'associer RLS et SSO en
Direct Lake, et la fonction *Tester en tant que rôle* ne fonctionne pas en SSO. Le lab lit donc OneLake avec une
identité fixe, celle du principal de service.

1. Fabric > Paramètres > **Gérer les connexions et les passerelles** > Nouveau, connexion cloud :

   | Connexion | Type | Paramètres | Authentification |
   |---|---|---|---|
   | `OneLake - SP AmazingZone` | Azure Data Lake Storage Gen2 | URL `https://onelake.dfs.fabric.microsoft.com/<ID de l'espace>/<ID du Warehouse AmazingZoneWH>/` | Principal de service (ID locataire, ID client, secret) |

   Partagez-la (**Gérer les utilisateurs**) avec `dp-equipedata`. Une connexion créée par le principal de service
   n'est visible de personne d'autre tant qu'il ne l'a pas partagée.
2. Paramètres du modèle > **Connexions de passerelle et cloud** : associez la source OneLake à
   `OneLake - SP AmazingZone`, et la source SharePoint (table `Budget`) à `SharePoint - Finance (SP AmazingZone)`
   si elle apparaît sans connexion. Le bouton **Appliquer** reste grisé tant que l'option *Utiliser une passerelle
   de données locale ou de réseau virtuel* n'est pas désactivée, même si elle est vide.
3. Sécurité du modèle > rôle **Lecteurs par entrepôt** : ajoutez les utilisateurs du seed, ou un groupe qui les
   contient. Les membres ne passent pas par la définition du modèle : un déploiement ne les apporte pas.
4. Actualisez le modèle, puis contrôlez avec **Tester en tant que rôle** et un utilisateur du seed : les montants
   doivent être ceux de la requête T-SQL de la section 10.2. Le rôle seul, sans utilisateur du seed, ne renvoie
   rien.

Le rôle ne filtre que les lecteurs : un membre de l'espace avec le rôle Administrateur, Membre ou Contributeur voit
tout. Distribuez donc le rapport par l'application d'organisation (audience) et non par les rôles de l'espace ; le
partage de l'application donne aux lecteurs la permission Read sur le modèle, il leur suffit d'être membres du rôle
RLS. La permission Build n'est utile qu'aux utilisateurs qui construisent leurs propres rapports sur le modèle.

## 10.4 Contrôle des tenant settings

Le notebook `Contrôle - Tenant settings` (dossier « 6 - Gouvernance ») lit les tenant settings par l'API
d'administration de Fabric, sous l'identité du principal de service, et les compare à
`gouvernance/tenant-settings-reference.json`. Il ne modifie rien.

1. Microsoft Entra > Groupes > Nouveau groupe : type **Sécurité**, nom `dp-api-admin-lecture`, avec
   `SP-Fabric-AmazingZone` pour seul membre.
2. Portail d'administration Fabric > Tenant settings > *Admin API settings* > **Service principals can access
   read-only admin APIs** : activé pour le groupe `dp-api-admin-lecture`. Comptez jusqu'à une heure avant que le
   principal de service y ait accès : dans le lab, l'API a répondu *403 InsufficientScopes* pendant 65 minutes
   après l'activation.
3. Adaptez la référence. Elle décrit le locataire du lab : les groupes `dp-equipedata` et `dp-api-admin-lecture`,
   un compte invité, la création d'espaces réservée à l'équipe Data. Dans un locataire partagé, ne reproduisez pas
   ces valeurs sans les discuter avec son administrateur : le notebook signale les écarts, il n'impose rien.
4. Déposez la référence dans le Lakehouse : `AmazingZoneLK` > Files > nouveau dossier `gouvernance` > Charger
   `tenant-settings-reference.json`. Le notebook lit cette copie ; rechargez-la à chaque modification du fichier
   du dépôt.
5. Exécutez le notebook une fois. Il lit le certificat du principal de service dans le coffre
   (`cert-sp-fabric-sharepoint`, guide 5) sous l'identité qui l'exécute, qui doit donc avoir accès au coffre.
   Il écrit deux tables Delta :

   ```sql
   -- Point de terminaison SQL de AmazingZoneLK
   SELECT statut, COUNT(*) FROM gouvernance.tenant_settings_ecarts
   WHERE date_controle = (SELECT MAX(date_controle) FROM gouvernance.tenant_settings_ecarts)
   GROUP BY statut;      -- conforme, écart, absent ; « nouveau » pour un paramètre apparu depuis le relevé précédent
   ```

   `gouvernance.tenant_settings_releve` garde l'état complet de chaque paramètre à chaque contrôle.
6. Vérifiez la planification (notebook > **Planifier**) : chaque lundi à 7 h, heure de Paris. Les dates de début
   et de fin sont celles du lab de l'auteur ; ajustez-les.

## 10.5 Ce que le dépôt ne contient pas

Le reste du chapitre 9 se règle dans les portails et ne passe pas par Git : les tenant settings eux-mêmes, la
protection de l'accès sortant (espace dédié sur une capacité F2, elle n'est pas disponible en évaluation), le
pare-feu IP de l'espace, les étiquettes de confidentialité de Microsoft Purview, le partage du modèle avec la
permission Build et le retrait des rôles nominatifs dans les espaces. Le chapitre décrit chacun de ces réglages
et la manière dont le lab les a appliqués.
