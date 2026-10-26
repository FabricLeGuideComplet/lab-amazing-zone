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

# # Synchronisation du Bronze
# # Première étape du pipeline « Orchestration - Transformation » : le job dbt lit le Bronze du Lakehouse
# AmazingZoneLK au travers de son point de terminaison SQL, qui se synchronise de lui-même, mais avec un délai.
# Le notebook demande donc la synchronisation des métadonnées, attend sa fin et échoue si une table n'a pas pu
# être synchronisée : dbt ne doit pas construire les couches Silver et Gold sur l'état de la veille.
# # Moteur Python (une seule machine) : le notebook ne fait qu'appeler l'API Fabric et attendre.

# CELL ********************

import json
import time

import requests

API = "https://api.fabric.microsoft.com/v1"
LAKEHOUSE = "AmazingZoneLK"
DELAI_MAX_MINUTES = 30


def appeler(methode, url, **kwargs):
    """Appel authentifié à l'API Fabric, avec l'identité qui exécute le notebook (aucun secret)."""
    jeton = notebookutils.credentials.getToken("pbi")
    reponse = requests.request(methode, url, headers={"Authorization": f"Bearer {jeton}"}, **kwargs)
    reponse.raise_for_status()
    return reponse


def attendre(url_suivi, libelle):
    """Suit une opération longue de l'API Fabric (202 + Location) jusqu'à son terme et renvoie son résultat."""
    debut = time.time()
    while time.time() - debut < DELAI_MAX_MINUTES * 60:
        time.sleep(10)
        etat = appeler("GET", url_suivi).json()
        statut = etat.get("status")
        if statut in ("Completed", "Succeeded"):
            return appeler("GET", url_suivi + "/result").json()
        if statut in ("Failed", "Cancelled"):
            raise RuntimeError(f"{libelle} : {statut} {json.dumps(etat.get('error'))}")
    raise TimeoutError(f"{libelle} : pas terminé après {DELAI_MAX_MINUTES} minutes")


espace = notebookutils.runtime.context["currentWorkspaceId"]
lakehouse = next(i for i in appeler("GET", f"{API}/workspaces/{espace}/lakehouses").json()["value"]
                 if i["displayName"] == LAKEHOUSE)
point_sql = appeler("GET", f"{API}/workspaces/{espace}/lakehouses/{lakehouse['id']}").json()[
    "properties"]["sqlEndpointProperties"]["id"]

reponse = appeler("POST", f"{API}/workspaces/{espace}/sqlEndpoints/{point_sql}/refreshMetadata", json={})
resultat = attendre(reponse.headers["Location"], "Synchronisation") if reponse.status_code == 202 else reponse.json()

# L'appel réussit même si une table échoue : le statut se lit table par table.
echecs = [t for t in resultat["value"] if t["status"] == "Failure"]
print(f"{len(resultat['value'])} tables, {len(echecs)} en échec")
if echecs:
    raise RuntimeError("Tables non synchronisées : " + ", ".join(
        f"{t['tableName']} ({t['error']['errorCode']})" for t in echecs))

notebookutils.notebook.exit(json.dumps({"point_sql": point_sql, "tables": len(resultat["value"])}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
