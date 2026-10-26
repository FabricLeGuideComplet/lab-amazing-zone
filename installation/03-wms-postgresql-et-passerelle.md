# 3. WMS PostgreSQL et passerelle de données

Le WMS d'Amazing Zone joue, dans le livre, la source « on-premise » : une base PostgreSQL sur un serveur Linux
que Fabric ne peut atteindre que par une passerelle de données locale. Le lab la simule avec deux VM Azure dans
un réseau virtuel sans exposition de PostgreSQL sur Internet : la VM de la passerelle est la seule à parler à la
base.

| Ressource | Nom dans le lab | Configuration |
|---|---|---|
| Groupe de ressources | `RG_WMS` | North Europe (une autre région que le site, comme un datacenter distinct) |
| Réseau virtuel | `WMSpostgre-vnet` | 10.0.0.0/16, sous-réseau `default` 10.0.0.0/24 |
| VM base | `WMSpostgre` | Ubuntu Server 24.04 LTS, Standard D2s v3, disque Premium SSD 30 Go, zone 1, IP privée 10.0.0.4, authentification SSH par clé (utilisateur `azureuser`), PostgreSQL 16 |
| VM passerelle | `WMSgateway` | Windows Server 2025 Datacenter (Gen2), Standard D2s v3, disque Premium SSD 127 Go, zone 1, IP privée 10.0.0.5, passerelle de données locale en mode standard |
| Groupes de sécurité réseau | `WMSpostgre-nsg`, `WMSgateway-nsg` | SSH (22) sur la VM base, RDP (3389) sur la VM passerelle, depuis votre adresse IP uniquement |
| Sous-réseau délégué (facultatif) | `snet-fabric-gateway` | 10.0.1.0/27, délégué à `Microsoft.PowerPlatform/vnetaccesslinks`, pour une passerelle de réseau virtuel (chapitre 4) |

Dans le lab de l'auteur, les règles SSH et RDP acceptent toutes les adresses sources ; limitez-les à la vôtre,
ou passez par Azure Bastion.

## 3.1 Réseau et machines virtuelles

```bash
RG=RG_WMS
REGION=northeurope
MON_IP=$(curl -s https://api.ipify.org)
ssh-keygen -t ed25519 -f ~/.ssh/wmspostgre_ed25519 -N ''        # clé dédiée au lab

az group create -n $RG -l $REGION
az network vnet create -g $RG -n WMSpostgre-vnet --address-prefixes 10.0.0.0/16 \
   --subnet-name default --subnet-prefixes 10.0.0.0/24

az network nsg create -g $RG -n WMSpostgre-nsg
az network nsg rule create -g $RG --nsg-name WMSpostgre-nsg -n SSH --priority 300 \
   --direction Inbound --access Allow --protocol Tcp --destination-port-ranges 22 --source-address-prefixes $MON_IP
az network nsg create -g $RG -n WMSgateway-nsg
az network nsg rule create -g $RG --nsg-name WMSgateway-nsg -n RDP --priority 300 \
   --direction Inbound --access Allow --protocol Tcp --destination-port-ranges 3389 --source-address-prefixes $MON_IP

az vm create -g $RG -n WMSpostgre --zone 1 \
   --image Canonical:ubuntu-24_04-lts:server:latest --size Standard_D2s_v3 \
   --os-disk-size-gb 30 --storage-sku Premium_LRS \
   --admin-username azureuser --ssh-key-values ~/.ssh/wmspostgre_ed25519.pub \
   --vnet-name WMSpostgre-vnet --subnet default --private-ip-address 10.0.0.4 \
   --nsg WMSpostgre-nsg --public-ip-sku Standard

az vm create -g $RG -n WMSgateway --zone 1 \
   --image MicrosoftWindowsServer:WindowsServer:2025-datacenter-g2:latest --size Standard_D2s_v3 \
   --storage-sku Premium_LRS \
   --admin-username wmsadmin --admin-password '<mot de passe fort>' \
   --vnet-name WMSpostgre-vnet --subnet default --private-ip-address 10.0.0.5 \
   --nsg WMSgateway-nsg --public-ip-sku Standard

# Arrêt automatique chaque soir (heure UTC), par précaution. La région doit être celle des VM :
# sans -l, la commande prend celle du groupe de ressources et échoue (InvalidScheduleLocation) si elles diffèrent.
az vm auto-shutdown -g $RG -n WMSpostgre --time 1900 -l $REGION
az vm auto-shutdown -g $RG -n WMSgateway --time 1900 -l $REGION
```

L'arrêt automatique désalloue la VM à l'heure dite ; en fin de séance, désallouez-les sans attendre avec
`az vm deallocate` (guide 9).

## 3.2 PostgreSQL 16 sur la VM base

```bash
IP_PG=$(az vm show -d -g RG_WMS -n WMSpostgre --query publicIps -o tsv)
ssh -i ~/.ssh/wmspostgre_ed25519 azureuser@$IP_PG
```

Sur la VM :

```bash
# Mode non interactif : sinon needrestart ouvre une boîte de dialogue en fin de mise à jour
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql   # Ubuntu 24.04 fournit PostgreSQL 16
psql --version                            # psql (PostgreSQL) 16.x

# Écoute sur l'adresse privée (par défaut, PostgreSQL n'écoute que localhost)
sudo -u postgres psql -c "ALTER SYSTEM SET listen_addresses = 'localhost,10.0.0.4';"

# Seule la VM de la passerelle peut se connecter, avec le rôle de lecture fabric_ingestion (guide 5)
echo "host  postgres  fabric_ingestion  10.0.0.5/32  scram-sha-256" | \
   sudo tee -a /etc/postgresql/16/main/pg_hba.conf
sudo systemctl restart postgresql
sudo ss -ltnp | grep 5432                 # 127.0.0.1:5432 et 10.0.0.4:5432
```

Le port 5432 n'a pas besoin de règle NSG : la règle par défaut `AllowVnetInBound` autorise le trafic entre les
deux VM du réseau virtuel, et rien ne l'ouvre depuis Internet.

## 3.3 Schéma du WMS

Copiez le dossier `wms` du dépôt sur la VM, depuis votre poste :

```bash
scp -i ~/.ssh/wmspostgre_ed25519 -r wms azureuser@$IP_PG:~/
```

Puis, sur la VM, créez le schéma et appliquez les migrations dans l'ordre :

```bash
cd ~/wms
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f init/wms_init.sql
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f migrations/001_date_maj.sql
sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f migrations/002_entrepot_commande.sql
```

| Script | Effet |
|---|---|
| `init/wms_init.sql` | Schéma `wms`, extension `pgcrypto`, 8 tables métier (`warehouse`, `location`, `item`, `customer`, `inventory`, `orders`, `order_line`, `shipment`) et un premier jeu de données ; la table technique `_order_no_raw` sert au chargement des numéros de commande. |
| `migrations/001_date_maj.sql` | Colonne `date_maj` (timestamptz), trigger `BEFORE UPDATE` et index sur les 8 tables : c'est le filigrane des chargements incrémentaux (Copy Job en CDC, chapitre 4). Les avertissements `trigger ... does not exist, skipping` au premier passage sont normaux. |
| `migrations/002_entrepot_commande.sql` | Colonne `warehouse_id` sur `wms.orders` : entrepôt de préparation de la commande. |

Les données de démonstration cohérentes avec le site (`donnees_demo/wms_demo.sql`) se chargent au guide 8,
après la génération des commandes du site. Contrôle rapide à ce stade :

```bash
sudo -u postgres psql -d postgres -c "\dt wms.*"
```

Les scripts sont rejouables : en cas d'erreur, corrigez et relancez.

## 3.4 Passerelle de données locale sur la VM Windows

1. Connectez-vous en Bureau à distance à `WMSgateway` (adresse IP publique de la VM, compte `wmsadmin`).
2. Téléchargez la **passerelle de données locale (mode standard)** depuis la page Microsoft Learn
   *Installer une passerelle de données locale*
   (<https://learn.microsoft.com/data-integration/gateway/service-gateway-install>) et lancez l'installation.
3. Connectez-vous avec votre compte professionnel du locataire du lab, choisissez **Inscrire une nouvelle
   passerelle sur cet ordinateur**, nommez-la `WMSgateway` et définissez une clé de récupération. Rangez cette clé
   dans votre gestionnaire de mots de passe : elle est indispensable pour restaurer ou migrer la passerelle.
4. Laissez la région proposée (celle de votre locataire Fabric), sauf contrainte particulière.
5. Vérifiez, toujours sur la VM, que la base est joignable :

```powershell
Test-NetConnection 10.0.0.4 -Port 5432        # TcpTestSucceeded : True
```

Dans Fabric, **Paramètres > Gérer les connexions et les passerelles > Passerelles de données locales**, la
passerelle `WMSgateway` apparaît en ligne. Ajoutez le groupe `dp-equipedata` à ses administrateurs, pour que la
passerelle ne dépende pas d'un seul compte. Le connecteur PostgreSQL est fourni avec la passerelle : aucun pilote
à installer. La connexion « PostgreSQL - WMS » qui l'utilise se crée au guide 7.

### Variante : installation sans Bureau à distance

L'installation du logiciel (étape 2) et le test réseau (étape 5) peuvent se faire depuis votre poste, avec la
commande d'exécution d'Azure. Le programme d'installation accepte un mode silencieux :

```powershell
# installer_passerelle.ps1
$ErrorActionPreference = 'Stop'
(Test-NetConnection 10.0.0.4 -Port 5432 -WarningAction SilentlyContinue).TcpTestSucceeded   # True attendu
$exe = "$env:TEMP\GatewayInstall.exe"
Invoke-WebRequest -UseBasicParsing "https://go.microsoft.com/fwlink/?LinkId=2116849&clcid=0x409" -OutFile $exe
$p = Start-Process $exe -ArgumentList '/quiet', 'ACCEPTEULA=yes' -Wait -PassThru
"Code retour : $($p.ExitCode)"                                                               # 0 attendu
Get-Service PBIEgwService | Format-Table Name, Status -AutoSize | Out-String                  # Running
```

```bash
az vm run-command invoke -g RG_WMS -n WMSgateway --command-id RunPowerShellScript \
   --scripts @installer_passerelle.ps1 --query "value[].message" -o tsv
```

Comptez une vingtaine de minutes : le programme télécharge la passerelle avant de l'installer, et la commande ne
rend la main qu'à la fin. Lors du rejeu d'octobre 2026, la version installée était la 3000.338.2.

L'inscription (étapes 3 et 4) demande toujours une connexion. Le module PowerShell `DataGateway` de Microsoft sait
inscrire une passerelle sans interface, mais toutes ses commandes, `Install-DataGateway` compris, exigent d'abord
`Connect-DataGatewayServiceAccount`, avec un compte ou un principal de service et son secret : il faudrait alors
faire transiter ce secret jusqu'à la VM. Le lab s'en tient à l'inscription par le Bureau à distance, avec votre
compte, qui ne prend que quelques minutes une fois le logiciel installé.

La passerelle ne fonctionne que si la VM est démarrée : une ingestion lancée VM éteinte échoue avec
`GatewayUnreachable`.

## 3.5 Sous-réseau délégué pour une passerelle de réseau virtuel (facultatif)

Le chapitre 4 compare la passerelle locale à la passerelle de réseau virtuel (VNet data gateway). Le lab prépare
le sous-réseau sans créer cette dernière :

```bash
az provider register --namespace Microsoft.PowerPlatform
az network vnet subnet create -g RG_WMS --vnet-name WMSpostgre-vnet -n snet-fabric-gateway \
   --address-prefixes 10.0.1.0/27 --delegations Microsoft.PowerPlatform/vnetaccesslinks
```

L'inscription du fournisseur de ressources se fait au niveau de l'abonnement : un principal de service qui n'est
contributeur que des groupes de ressources ne peut pas la faire.

## 3.6 Le module temps réel

Le module Python qui, dans le livre, envoie chaque événement logistique en temps réel est simulé par
`wms/temps_reel/simulateur_evenements.py`, exécuté depuis votre poste vers l'Eventstream « Flux - Événements
WMS ». Il ne dépend pas des VM ; sa mise en route est décrite au guide 8.
