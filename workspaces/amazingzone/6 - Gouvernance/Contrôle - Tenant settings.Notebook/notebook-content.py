# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.12"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "f6523eec-e450-401b-a672-cebe8d1ef2af",
# META       "default_lakehouse_name": "AmazingZoneLK",
# META       "default_lakehouse_workspace_id": "0875373d-96cd-4d0e-b4e7-5fc5cd327cb8",
# META       "known_lakehouses": [
# META         {
# META           "id": "f6523eec-e450-401b-a672-cebe8d1ef2af"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Contrôle des tenant settings
# Compare chaque semaine les tenant settings réels du tenant à la référence versionnée dans le dépôt
# (`gouvernance/tenant-settings-reference.json`, copiée dans `Files/gouvernance/` du Lakehouse AmazingZoneLK) et
# écrit le résultat dans deux tables Delta du schéma `gouvernance` :
# - `gouvernance.tenant_settings_releve` : l'état complet de chaque paramètre à chaque contrôle (en ajout), ce qui
#   permet de repérer les paramètres apparus depuis le contrôle précédent ;
# - `gouvernance.tenant_settings_ecarts` : une ligne par paramètre de la référence et par contrôle, avec son statut
#   (conforme, écart, absent) ; les paramètres apparus depuis le dernier relevé y figurent avec le statut « nouveau ».
# - Lecture par l'API d'administration de Fabric (`GET /v1/admin/tenantsettings`) sous l'identité du principal de
#   service SP-Fabric-AmazingZone, membre du groupe dp-api-admin-lecture autorisé par le paramètre « Service
#   principals can access read-only admin APIs ». Le jeton est obtenu avec le certificat du principal de service,
#   rangé dans le coffre kv-amazingzone-lab et lu par notebookutils.credentials.getSecret sous l'identité qui
#   exécute le notebook.
# - Moteur : notebook **Python** ; `azure-identity` et `deltalake` sont préinstallées.

# PARAMETERS CELL ********************

# Les trois premières valeurs sont remplacées au déploiement (parameter.yml, variables de .env)
TENANT_ID = "<AZURE_TENANT_ID>"
CLIENT_ID = "<AZURE_CLIENT_ID>"   # SP-Fabric-AmazingZone
COFFRE_URI = "https://kv-amazingzone-lab.vault.azure.net/"
NOM_CERTIFICAT = "cert-sp-fabric-sharepoint"
REFERENCE = "/lakehouse/default/Files/gouvernance/tenant-settings-reference.json"
SCHEMA = "gouvernance"

# CELL ********************

import base64
import json
import os
from datetime import datetime, timezone

import pandas as pd
import requests
from azure.identity import CertificateCredential
from deltalake import DeltaTable, write_deltalake

# Jeton du principal de service : le certificat (PKCS#12) est lu dans le coffre, jamais écrit sur disque.
pfx = base64.b64decode(notebookutils.credentials.getSecret(COFFRE_URI, NOM_CERTIFICAT))
jeton = CertificateCredential(TENANT_ID, CLIENT_ID, certificate_data=pfx).get_token(
    "https://api.fabric.microsoft.com/.default").token

reponse = requests.get("https://api.fabric.microsoft.com/v1/admin/tenantsettings",
                       headers={"Authorization": f"Bearer {jeton}"}, timeout=60)
reponse.raise_for_status()   # 403 InsufficientScopes : le principal n'est pas (encore) autorisé par le paramètre
reels = {t["settingName"]: t for t in reponse.json()["tenantSettings"]}
reference = json.load(open(REFERENCE, encoding="utf-8"))
controle = datetime.now(timezone.utc)
print(f"{len(reels)} paramètres lus, {len(reference['parametres'])} dans la référence (version {reference['version']})")

# CELL ********************

def groupes(parametre):
    return sorted(g["name"] for g in parametre.get("enabledSecurityGroups", []))

racine = "/lakehouse/default"
storage_options = {"use_fabric_endpoint": "true", "allow_unsafe_rename": "true"}
chemin_releve = f"{racine}/Tables/{SCHEMA}/tenant_settings_releve"
chemin_ecarts = f"{racine}/Tables/{SCHEMA}/tenant_settings_ecarts"

# Paramètres apparus depuis le relevé précédent
try:
    precedent = DeltaTable(chemin_releve, storage_options=storage_options).to_pandas()
    derniers = set(precedent.loc[precedent["date_controle"] == precedent["date_controle"].max(), "setting_name"])
except Exception:
    derniers = set()

lignes = []
for p in reference["parametres"]:
    reel = reels.get(p["settingName"])
    attendu = p["attendu"]
    if reel is None:
        statut, actif, grp = "absent", None, ""
    else:
        actif, grp = reel["enabled"], ", ".join(groupes(reel))
        conforme = actif == attendu["enabled"] and groupes(reel) == sorted(attendu["groupes"])
        statut = "conforme" if conforme else "écart"
    lignes.append({"date_controle": controle, "setting_name": p["settingName"], "titre": p["titre"],
                   "statut": statut, "attendu_actif": attendu["enabled"], "attendu_groupes": ", ".join(attendu["groupes"]),
                   "reel_actif": actif, "reel_groupes": grp, "justification": p["justification"], "source": p["source"]})
if derniers:
    for nom in sorted(set(reels) - derniers):
        r = reels[nom]
        lignes.append({"date_controle": controle, "setting_name": nom, "titre": r["title"], "statut": "nouveau",
                       "attendu_actif": None, "attendu_groupes": "", "reel_actif": r["enabled"],
                       "reel_groupes": ", ".join(groupes(r)), "justification": "À examiner et à ajouter à la référence",
                       "source": ""})

ecarts = pd.DataFrame(lignes).astype({"attendu_actif": "boolean", "reel_actif": "boolean"})
releve = pd.DataFrame([{"date_controle": controle, "setting_name": n, "titre": r["title"],
                        "groupe_parametres": r.get("tenantSettingGroup", ""), "actif": r["enabled"],
                        "groupes": ", ".join(groupes(r))} for n, r in reels.items()])

for chemin, donnees in ((chemin_ecarts, ecarts), (chemin_releve, releve)):
    os.makedirs(chemin, exist_ok=True)
    write_deltalake(chemin, donnees, mode="append", schema_mode="merge", storage_options=storage_options)

resume = ecarts["statut"].value_counts().to_dict()
print(resume)
display(ecarts[ecarts["statut"] != "conforme"])
