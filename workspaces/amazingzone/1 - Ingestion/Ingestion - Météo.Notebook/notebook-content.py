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

# # Ingestion des prévisions météo (Open-Meteo)
# Interroge l'API publique Open-Meteo pour chaque site d'Amazing Zone (entrepôts) et alimente deux tables Delta
# du schéma `meteo` (Bronze, un schéma par source) du Lakehouse AmazingZoneLK :
# - `meteo.weather_forecast` : une ligne par site et par jour, fusionnée à chaque exécution (les valeurs consolidées
#   des jours passés remplacent les prévisions) ; sert au reporting.
# - `meteo.weather_forecast_issued` : chaque prévision telle qu'elle a été émise (date d'émission, échéance), en ajout :
#   c'est la seule information dont la logistique dispose au moment de planifier, et celle que le Machine Learning
#   doit utiliser pour ne pas apprendre sur la météo observée.
# - Moteur : notebook **Python** (une seule machine, pas de cluster Spark).
# - Aucune bibliothèque à installer : appel HTTP en bibliothèque standard, écriture avec `deltalake` (préinstallée).
# - Les paramètres ci-dessous peuvent être surchargés par l'activité Notebook d'un pipeline.
# - Offre commerciale : l'usage d'Open-Meteo par une entreprise relève de l'offre payante (point de terminaison
#   customer-api et clé d'API), dont la clé est rangée dans le coffre kv-amazingzone-lab. Le dépôt montre les deux
#   façons de la lire : par le notebook lui-même, avec notebookutils.credentials.getSecret (chapitre 4), sous l'identité
#   qui l'exécute ; ou par le pipeline « Orchestration - Ingestion » (activité Web, chapitre 9), qui la transmet en
#   paramètre sécurisé. L'environnement de démonstration reste sur l'offre gratuite.

# PARAMETERS CELL ********************

# Sites interrogés (JSON) : code du site, libellé, coordonnées
SITES_JSON = """[
  {"site": "WH1", "nom": "Entrepôt principal - Saran (Orléans)", "latitude": 47.95, "longitude": 1.88},
  {"site": "WH2", "nom": "Entrepôt Saint-Quentin-Fallavier (Lyon)", "latitude": 45.64, "longitude": 5.11},
  {"site": "WH3", "nom": "Entrepôt Lesquin (Lille)", "latitude": 50.59, "longitude": 3.11},
  {"site": "WH4", "nom": "Entrepôt Vitrolles (Marseille)", "latitude": 43.46, "longitude": 5.25}
]"""
JOURS_PASSES = 7        # jours d'historique relus à chaque exécution (les observations remplacent les prévisions)
JOURS_PREVISION = 4     # horizon de prévision : le modèle Météo-France ne couvre que les 4 prochains jours
MODELE = "meteofrance_seamless"
TARGET_SCHEMA = "meteo"
TARGET_TABLE = "weather_forecast"
TABLE_EMISSIONS = "weather_forecast_issued"
OFFRE_COMMERCIALE = False   # True : point de terminaison customer-api et clé d'API
CLE_API = ""                # transmise par le pipeline (activité Web sur le coffre), jamais saisie ici ;
                            # vide : le notebook la lit lui-même dans le coffre
COFFRE_URI = "https://kv-amazingzone-lab.vault.azure.net/"
NOM_SECRET = "open-meteo-cle-api"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import pandas as pd
from deltalake import DeltaTable, write_deltalake

VARIABLES = [
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "apparent_temperature_max", "apparent_temperature_min",
    "sunrise", "sunset", "daylight_duration", "sunshine_duration", "uv_index_max",
    "rain_sum", "showers_sum", "snowfall_sum", "precipitation_sum",
    "wind_gusts_10m_max", "wind_direction_10m_dominant", "wind_speed_10m_max",
]

# Clé de l'offre commerciale : transmise par le pipeline (activité Web sur le coffre, chapitre 9) ou, à défaut, lue ici
# dans le coffre (chapitre 4). getSecret s'authentifie avec l'identité qui exécute le notebook : l'utilisateur en
# exécution manuelle ; dans un pipeline, la connexion de l'activité Notebook (principal de service ou identité de
# l'espace) ou, sans connexion, le dernier utilisateur à avoir modifié le pipeline.
if OFFRE_COMMERCIALE and not CLE_API:
    CLE_API = notebookutils.credentials.getSecret(COFFRE_URI, NOM_SECRET)


def appeler_open_meteo(site: dict, tentatives: int = 3) -> pd.DataFrame:
    """Prévisions quotidiennes d'un site, une ligne par jour."""
    params = {
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "daily": ",".join(VARIABLES),
        "models": MODELE,
        "timezone": "Europe/Paris",
        "past_days": JOURS_PASSES,
        "forecast_days": JOURS_PREVISION,
    }
    if OFFRE_COMMERCIALE:
        params["apikey"] = CLE_API
        hote = "https://customer-api.open-meteo.com"
    else:
        hote = "https://api.open-meteo.com"
    # L'URL contient la clé avec l'offre commerciale : elle n'est jamais affichée ni journalisée
    url = f"{hote}/v1/forecast?" + urllib.parse.urlencode(params)
    for essai in range(1, tentatives + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as reponse:
                donnees = json.load(reponse)
            break
        except Exception as erreur:
            if essai == tentatives:
                # message sans l'URL, qui porte la clé d'API avec l'offre commerciale
                raise RuntimeError(f"Open-Meteo injoignable pour le site {site['site']} : {type(erreur).__name__}") from None
            time.sleep(2 ** essai)

    df = pd.DataFrame(donnees["daily"]).rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for col in VARIABLES:
        if col in ("sunrise", "sunset"):
            # heures locales converties en UTC avec fuseau : un horodatage sans fuseau serait écrit
            # en timestamp_ntz, type que le SQL Analytics Endpoint ignore
            df[col] = (pd.to_datetime(df[col]).dt.tz_localize("Europe/Paris", ambiguous="NaT", nonexistent="NaT")
                       .dt.tz_convert("UTC").dt.as_unit("us"))
        else:
            # typage explicite : une variable sans valeur pour le modèle arriverait sinon en type « Null »,
            # que Delta Lake refuse
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    df.insert(0, "site", site["site"])
    df.insert(1, "site_nom", site["nom"])
    df["latitude"] = float(site["latitude"])
    df["longitude"] = float(site["longitude"])
    return df

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

sites = json.loads(SITES_JSON)
extraction_utc = pd.Timestamp(datetime.now(timezone.utc)).as_unit("us")

meteo = pd.concat([appeler_open_meteo(s) for s in sites], ignore_index=True)
meteo["date_extraction_utc"] = extraction_utc

print(f"{len(meteo)} lignes pour {len(sites)} site(s), du {meteo['date'].min()} au {meteo['date'].max()}")
display(meteo.head())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

chemin = f"/lakehouse/default/Tables/{TARGET_SCHEMA}/{TARGET_TABLE}"
storage_options = {"use_fabric_endpoint": "true", "allow_unsafe_rename": "true"}
os.makedirs(chemin, exist_ok=True)

existe = DeltaTable.is_deltatable(chemin, storage_options=storage_options)
colonnes = [f.name for f in DeltaTable(chemin, storage_options=storage_options).schema().fields] if existe else []

if existe and "site" in colonnes:
    # Fusion par site et par jour : les prévisions sont remplacées par les valeurs les plus récentes
    resultat = (
        DeltaTable(chemin, storage_options=storage_options)
        .merge(source=meteo, predicate="t.site = s.site AND t.date = s.date",
               source_alias="s", target_alias="t")
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute()
    )
    mode = "fusion"
else:
    # Première exécution (ou ancienne structure sans colonne site) : création de la table
    write_deltalake(chemin, meteo, mode="overwrite", schema_mode="overwrite", storage_options=storage_options)
    resultat = {"num_target_rows_inserted": len(meteo)}
    mode = "création"

print(mode, resultat)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# Prévisions telles qu'émises : une ligne par site, jour d'émission et jour prévu (échéance 0 à 3 jours).
# Fusion sur ces trois colonnes, pour qu'une réexécution le même jour remplace la prévision du jour sans doublon.
COLONNES_PREVISION = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "snowfall_sum",
                      "wind_gusts_10m_max"]
date_emission = pd.Timestamp(extraction_utc).tz_convert("Europe/Paris").date()
emises = meteo[meteo["date"] >= date_emission][["site", "site_nom", "date"] + COLONNES_PREVISION].copy()
emises.insert(2, "date_emission", date_emission)
emises.insert(3, "echeance_jours", [(d - date_emission).days for d in emises["date"]])
emises["echeance_jours"] = emises["echeance_jours"].astype("int32")
emises["source"] = "forecast"
emises["modele"] = MODELE
emises["date_extraction_utc"] = extraction_utc

chemin_emissions = f"/lakehouse/default/Tables/{TARGET_SCHEMA}/{TABLE_EMISSIONS}"
os.makedirs(chemin_emissions, exist_ok=True)
if DeltaTable.is_deltatable(chemin_emissions, storage_options=storage_options):
    resultat_emissions = (
        DeltaTable(chemin_emissions, storage_options=storage_options)
        .merge(source=emises,
               predicate="t.site = s.site AND t.date_emission = s.date_emission AND t.date = s.date",
               source_alias="s", target_alias="t")
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute()
    )
else:
    write_deltalake(chemin_emissions, emises, mode="overwrite", schema_mode="overwrite", storage_options=storage_options)
    resultat_emissions = {"num_target_rows_inserted": len(emises)}
print("prévisions émises :", resultat_emissions)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

notebookutils.notebook.exit(json.dumps({
    "mode": mode,
    "sites": len(sites),
    "lignes_lues": int(len(meteo)),
    "lignes_inserees": int(resultat.get("num_target_rows_inserted", 0)),
    "lignes_mises_a_jour": int(resultat.get("num_target_rows_updated", 0)),
    "previsions_emises": int(len(emises)),
}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
