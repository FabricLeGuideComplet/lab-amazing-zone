# 5. Coffre de clés

Le coffre de clés `kv-amazingzone-lab` range les trois secrets du lab : le certificat du principal de service
pour SharePoint, le mot de passe du rôle PostgreSQL de lecture et la clé d'API météo. Fabric les lit au travers
d'une référence Azure Key Vault (chapitre 9) ; aucun secret n'est saisi dans une connexion ni écrit dans le code.

| Élément | Nom dans le lab | Usage |
|---|---|---|
| Coffre | `kv-amazingzone-lab` | Groupe `RG_AmazingZone`, France Central, niveau Standard, modèle d'autorisation **Azure RBAC**, suppression réversible 7 jours |
| Certificat | `cert-sp-fabric-sharepoint` | Authentification du principal de service auprès de SharePoint (connexion du Dataflow) et du coffre lui-même (connexion Web de l'activité « Cle API meteo ») ; validité 12 mois |
| Secret | `wms-postgresql-fabric-ingestion` | Mot de passe du rôle PostgreSQL `fabric_ingestion` (connexion « PostgreSQL - WMS ») |
| Secret | `open-meteo-cle-api` | Clé de l'offre commerciale d'Open-Meteo. Le lab reste sur l'offre gratuite : la valeur est fictive, mais le pipeline la lit pour montrer le mécanisme |
| Rôles | `Key Vault Secrets Officer`, `Key Vault Certificates Officer` | Attribués au groupe `dp-equipedata` sur le coffre ; le principal de service en hérite par son appartenance au groupe |

## 5.1 Créer le coffre

```bash
RG=RG_AmazingZone
KV=kv-amazingzone-<suffixe>              # nom unique, 24 caractères au plus
GROUPE_ID=$(az ad group show --group dp-equipedata --query id -o tsv)

az keyvault create -g $RG -n $KV -l francecentral --sku standard \
   --enable-rbac-authorization true --retention-days 7
KV_ID=$(az keyvault show -n $KV --query id -o tsv)

for ROLE in "Key Vault Secrets Officer" "Key Vault Certificates Officer"; do
  az role assignment create --assignee-object-id $GROUPE_ID --assignee-principal-type Group \
     --role "$ROLE" --scope $KV_ID
done
```

Les attributions de rôle mettent quelques minutes à s'appliquer. Si vous partez d'un coffre en stratégies d'accès,
le passage en RBAC (Paramètres > Configuration de l'accès > Contrôle d'accès en fonction du rôle Azure) exige un
compte Propriétaire ou Administrateur de l'accès utilisateur dont l'attribution ne porte pas de condition.

## 5.2 Certificat du principal de service

Le coffre génère un certificat auto-signé dont la clé privée ne le quitte pas ; seule la partie publique est
déposée sur l'inscription d'application.

```bash
az keyvault certificate get-default-policy > politique.json
python3 - <<'EOF'
import json
p = json.load(open("politique.json"))
p["x509CertificateProperties"]["subject"] = "CN=SP-Fabric-AmazingZone"
p["x509CertificateProperties"]["validityInMonths"] = 12
json.dump(p, open("politique.json", "w"), indent=1)
EOF
az keyvault certificate create --vault-name $KV -n cert-sp-fabric-sharepoint -p @politique.json

# Partie publique, déposée sur l'inscription d'application (sans retirer le secret client)
az keyvault certificate download --vault-name $KV -n cert-sp-fabric-sharepoint \
   -f cert-sp-fabric-sharepoint.pem -e PEM
APP_ID=$(az ad app list --display-name SP-Fabric-AmazingZone --query "[0].appId" -o tsv)
az ad app credential reset --id $APP_ID --cert @cert-sp-fabric-sharepoint.pem --append
rm politique.json cert-sp-fabric-sharepoint.pem
```

Vérification : Microsoft Entra > Inscriptions d'applications > `SP-Fabric-AmazingZone` > Certificats et secrets :
l'onglet Certificats affiche l'empreinte du certificat, l'onglet Secrets clients conserve le secret des scripts.

Notez l'échéance : à expiration, le Dataflow des référentiels et l'activité « Cle API meteo » échouent. Le
chapitre 9 décrit le renouvellement.

## 5.3 Secrets

### Mot de passe du rôle PostgreSQL de lecture

Le mot de passe est généré sur votre poste, rangé dans le coffre, puis transmis une seule fois à la VM pour créer
le rôle (VM `WMSpostgre` démarrée, dossier `wms` déjà copié au guide 3). Il n'est écrit sur aucun disque.

```bash
MDP=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-32)
az keyvault secret set --vault-name $KV -n wms-postgresql-fabric-ingestion --value "$MDP" -o none

IP_PG=$(az vm show -d -g RG_WMS -n WMSpostgre --query publicIps -o tsv)
printf '%s\n' "$MDP" | ssh -i ~/.ssh/wmspostgre_ed25519 azureuser@$IP_PG \
   "cd ~/wms && sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f init/role_fabric_ingestion.sql"
unset MDP
```

Le mot de passe voyage sur l'entrée standard de la session SSH : le script le lit avec `\prompt`, si bien qu'il
n'apparaît ni dans une ligne de commande ni dans la liste des processus de la VM.

Le script `wms/init/role_fabric_ingestion.sql` crée le rôle `fabric_ingestion` (ou change son mot de passe s'il
existe), lui donne `CONNECT` sur la base, `USAGE` sur le schéma `wms` et `SELECT` sur ses tables, y compris celles
que créeront les migrations suivantes. Le rôle ne peut rien modifier : un `DELETE` renvoie *permission denied*.
La ligne `pg_hba.conf` du guide 3 ne l'autorise que depuis la VM de la passerelle.

### Clé d'API météo

```bash
az keyvault secret set --vault-name $KV -n open-meteo-cle-api --value "cle-fictive-offre-gratuite" -o none
```

Le notebook « Ingestion - Météo » n'utilise la clé que si son paramètre `OFFRE_COMMERCIALE` vaut `True` ; avec
l'offre gratuite, il appelle l'API publique sans clé.

## 5.4 Référence Azure Key Vault dans Fabric

Fabric > Paramètres > **Gérer les connexions et les passerelles** > onglet **Références Azure Key Vault** >
Nouveau :

| Champ | Valeur |
|---|---|
| Nom | `kv-amazingzone-lab` |
| URI du coffre | `https://<coffre>.vault.azure.net/` |
| Authentification | OAuth 2.0, avec votre compte (membre de `dp-equipedata`, donc lecteur des secrets) |
| Utilisation par les connexions de passerelle | Cochée : la connexion « PostgreSQL - WMS » passe par la passerelle locale |

Puis **Gérer les utilisateurs** de la référence : ajoutez `SP-Fabric-AmazingZone` et `dp-equipedata` avec le rôle
Utilisateur. Sans ce partage, toute exécution portée par le principal de service (Copy Job, pipeline) échoue avec
`DMTS_UserIsNotAllowedToAccessAzureKeyVaultConnectionErrorCode`.

La référence sert ensuite aux connexions du guide 7 : mot de passe de « PostgreSQL - WMS », certificat de
« SharePoint - Finance (SP AmazingZone) » et de « Key Vault - SP AmazingZone ».
