# 4. SharePoint et référentiels Excel

Les référentiels d'Amazing Zone vivent dans des classeurs Excel du site SharePoint de la direction financière.
Le Dataflow Gen2 « Ingestion - Referentiels Excel » les charge dans le schéma `referentiels` du Lakehouse
(chapitre 4), et le modèle sémantique « Ventes et logistique » importe le budget des ventes (chapitre 6). Le
Dataflow lit SharePoint avec le principal de service du lab, limité à ce seul site.

## 4.1 Site Finance et emplacement des fichiers

1. SharePoint > Créer un site > **Site d'équipe**, nom `Finance`, adresse `https://<locataire>.sharepoint.com/sites/Finance`.
2. Choisissez le **français** comme langue du site : la bibliothèque par défaut s'appelle alors « Documents
   partagés » et son URL `Documents partages`, celle qu'attendent le Dataflow et le modèle sémantique. Avec un site
   en anglais, l'URL devient `Shared Documents` et il faut corriger les chemins dans le code M des deux éléments.
3. Déposez les fichiers suivants :

| Fichier (dossier `referentiels/` du dépôt) | Emplacement dans « Documents partagés » | Feuille lue | Table ou élément alimenté |
|---|---|---|---|
| `referentiel_geographique.xlsx` | `Referentiels/` | `Départements` | `referentiels.geographie` (101 départements, régions 2016) |
| `taux_de_change_vs_eur_2019_2026.xlsx` (non versionné, voir 4.2) | `Taux de change/` | `Taux de change vs EUR` | `referentiels.taux_change` |
| `budget_ventes_2026.xlsx` | racine de la bibliothèque | `Budget` | table `Budget` (Import) du modèle « Ventes et logistique » : 84 lignes, un mois par univers de produits, 800 000 € |

Les chemins complets lus par le lab sont donc :

```
https://<locataire>.sharepoint.com/sites/Finance/Documents partages/Referentiels/referentiel_geographique.xlsx
https://<locataire>.sharepoint.com/sites/Finance/Documents partages/Taux de change/taux_de_change_vs_eur_2019_2026.xlsx
https://<locataire>.sharepoint.com/sites/Finance/Documents%20partages/budget_ventes_2026.xlsx
```

Le nom d'hôte `<locataire>.sharepoint.com` est remplacé au déploiement par la variable `SHAREPOINT_HOTE`
(guide 7) ; le reste du chemin doit correspondre.

## 4.2 Classeur des taux de change

Le classeur n'est pas versionné dans ce dépôt. Si vous le reconstituez, respectez la structure attendue par le
Dataflow : une feuille `Taux de change vs EUR`, une ligne d'en-tête, puis une ligne par pays.

| Colonne | Contenu | Exemple |
|---|---|---|
| `Code ISO-3` | Code pays ISO 3166-1 alpha-3 | `JPN` |
| `Pays` | Nom du pays | `Japon` |
| `Code devise` | Code devise ISO 4217 | `JPY` |
| `Devise` | Nom de la devise | `Yen` |
| `2019` à `2026` | Taux annuel moyen contre l'euro (unités de devise pour un euro), numérique | `163,6` en 2024 |

Le Dataflow dépivote les colonnes d'années (`Annee`, `TauxChange`) et ne garde que les codes. Le lab en compte
1 984 lignes pour 153 devises. Les taux de référence de la Banque centrale européenne ou les statistiques
d'Eurostat conviennent comme source.

## 4.3 Accès du principal de service limité au site Finance

Le principal de service ne reçoit aucun droit global sur SharePoint : il ne lit que le site Finance, grâce à
l'autorisation `Sites.Selected`. Le chapitre 4 explique pourquoi l'autorisation `Sites.Read.All`, plus simple à
accorder, est à proscrire : elle ouvre en lecture tous les sites du locataire.

### Autorisations d'application

Microsoft Entra > Inscriptions d'applications > `SP-Fabric-AmazingZone` > **Autorisations de l'API** :

1. Ajouter une autorisation > Microsoft Graph > Autorisations d'application > `Sites.Selected`.
2. Ajouter une autorisation > SharePoint > Autorisations d'application > `Sites.Selected`.
3. **Accorder un consentement d'administrateur** pour le locataire.

À ce stade, le principal de service n'a accès à aucun site : `Sites.Selected` n'ouvre que les sites qu'on lui
attribue un par un.

### Attribution du site

L'attribution se fait par l'API Microsoft Graph, avec un compte administrateur qui détient, lui, l'autorisation
déléguée `Sites.FullControl.All`. Avec Microsoft Graph PowerShell :

```powershell
Install-Module Microsoft.Graph.Sites -Scope CurrentUser
Connect-MgGraph -Scopes "Sites.FullControl.All"

$site = Get-MgSite -SiteId "<locataire>.sharepoint.com:/sites/Finance"
New-MgSitePermission -SiteId $site.Id -BodyParameter @{
    roles = @("read")
    grantedToIdentities = @(@{ application = @{ id = "<ID d'application>"; displayName = "SP-Fabric-AmazingZone" } })
}
Get-MgSitePermission -SiteId $site.Id      # l'application apparaît avec le rôle read
```

L'équivalent dans l'Afficheur Graph (Graph Explorer) : `GET /v1.0/sites/<locataire>.sharepoint.com:/sites/Finance`
pour obtenir l'identifiant du site, puis `POST /v1.0/sites/{id}/permissions` avec le même corps. C'est l'appelant
qui a besoin de `Sites.FullControl.All`, pas le principal de service.

### Authentification par certificat

SharePoint refuse les jetons d'application obtenus avec un secret client (*Unsupported app only token*) : le
principal de service doit s'authentifier avec un certificat. Celui du lab, `cert-sp-fabric-sharepoint`, est créé
dans le coffre de clés au guide 5, et la connexion Fabric qui l'utilise au guide 7.

Une fois le certificat en place, le jeton du principal de service ne porte que le rôle `Sites.Selected` : un appel
à la racine du locataire répond 403, un appel au site Finance répond 200.

## 4.4 Modèle sémantique et budget

La table `Budget` du modèle « Ventes et logistique » est en mode Import, à côté des tables Direct Lake (modèle
composite, chapitre 6). Après le déploiement, renseignez ses informations d'identification dans les paramètres
du modèle sémantique > Informations d'identification de la source de données, avec un compte qui lit le site
Finance (OAuth2).
