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

# # Reprise de l'historique météo (Open-Meteo)
# # Exécution ponctuelle, sur une période donnée, pour les quatre entrepôts d'Amazing Zone :
# 1. valeurs quotidiennes consolidées (historical forecast API) fusionnées dans `meteo.weather_forecast`, avec le
#    même modèle et les mêmes variables que l'ingestion quotidienne (« Ingestion - Météo ») ;
# 2. prévisions émises la veille de chaque jour (previous runs API, variables horaires `_previous_day1` agrégées
#    à la journée, heure de Paris) ajoutées à `meteo.weather_forecast_issued`, avec l'échéance 1 : c'est l'historique
#    dont la table de caractéristiques du Machine Learning a besoin pour être entraînée sur des prévisions, et non sur
#    la météo observée. Les rafales prévues par Météo-France ne sont archivées que depuis le 7 août 2026 : avant cette
#    date, la colonne reste vide.
# # - Moteur : notebook **Python** (une seule machine, pas de cluster Spark).
# - Aucune bibliothèque à installer : appel HTTP en bibliothèque standard, écriture avec `deltalake` (préinstallée).
# - Les paramètres ci-dessous peuvent être surchargés par l'activité Notebook d'un pipeline.

# PARAMETERS CELL ********************

# Sites interrogés (JSON) : code du site, libellé, coordonnées
SITES_JSON = """[
  {"site": "WH1", "nom": "Entrepôt principal - Saran (Orléans)", "latitude": 47.95, "longitude": 1.88},
  {"site": "WH2", "nom": "Entrepôt Saint-Quentin-Fallavier (Lyon)", "latitude": 45.64, "longitude": 5.11},
  {"site": "WH3", "nom": "Entrepôt Lesquin (Lille)", "latitude": 50.59, "longitude": 3.11},
  {"site": "WH4", "nom": "Entrepôt Vitrolles (Marseille)", "latitude": 43.46, "longitude": 5.25}
]"""
DATE_DEBUT = "2025-01-01"   # premier jour repris
DATE_FIN = ""               # dernier jour repris (vide = avant-hier)
MODELE = "meteofrance_seamless"
TARGET_SCHEMA = "meteo"
TARGET_TABLE = "weather_forecast"
TABLE_EMISSIONS = "weather_forecast_issued"

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
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from deltalake import DeltaTable, write_deltalake

VARIABLES = [
    "weather_code", "temperature_2m_max", "temperature_2m_min",
    "apparent_temperature_max", "apparent_temperature_min",
    "sunrise", "sunset", "daylight_duration", "sunshine_duration", "uv_index_max",
    "rain_sum", "showers_sum", "snowfall_sum", "precipitation_sum",
    "wind_gusts_10m_max", "wind_direction_10m_dominant", "wind_speed_10m_max",
]


def appeler_open_meteo(site: dict, tentatives: int = 3) -> pd.DataFrame:
    """Valeurs quotidiennes passées d'un site, une ligne par jour."""
    params = {
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "daily": ",".join(VARIABLES),
        "models": MODELE,
        "timezone": "Europe/Paris",
        "start_date": DATE_DEBUT,
        "end_date": DATE_FIN or (date.today() - timedelta(days=2)).isoformat(),
    }
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    for essai in range(1, tentatives + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as reponse:
                donnees = json.load(reponse)
            break
        except Exception:
            if essai == tentatives:
                raise
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

# Prévisions émises la veille (échéance 1) : variables horaires « _previous_day1 » de la previous runs API,
# agrégées par jour local. Même modèle que l'ingestion quotidienne.
HORAIRES = {"temperature_2m": ("temperature_2m_max", "max", "temperature_2m_min", "min"),
            "precipitation": ("precipitation_sum", "sum"),
            "snowfall": ("snowfall_sum", "sum"),
            "wind_gusts_10m": ("wind_gusts_10m_max", "max")}


def previsions_veille(site: dict, tentatives: int = 3) -> pd.DataFrame:
    params = {
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "hourly": ",".join(f"{v}_previous_day1" for v in HORAIRES),
        "models": MODELE,
        "timezone": "Europe/Paris",
        "start_date": DATE_DEBUT,
        "end_date": DATE_FIN or (date.today() - timedelta(days=1)).isoformat(),
    }
    url = "https://previous-runs-api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    for essai in range(1, tentatives + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as reponse:
                donnees = json.load(reponse)
            break
        except Exception:
            if essai == tentatives:
                raise
            time.sleep(2 ** essai)
    hor = pd.DataFrame(donnees["hourly"])
    hor["date"] = pd.to_datetime(hor["time"]).dt.date
    for v in HORAIRES:
        hor[v] = pd.to_numeric(hor[f"{v}_previous_day1"], errors="coerce").astype("float64")
    jour = hor.groupby("date").agg(
        temperature_2m_max=("temperature_2m", "max"), temperature_2m_min=("temperature_2m", "min"),
        precipitation_sum=("precipitation", lambda x: x.sum(min_count=1)),
        snowfall_sum=("snowfall", lambda x: x.sum(min_count=1)),
        wind_gusts_10m_max=("wind_gusts_10m", "max")).reset_index()
    jour.insert(0, "site", site["site"])
    jour.insert(1, "site_nom", site["nom"])
    jour.insert(3, "date_emission", [d - timedelta(days=1) for d in jour["date"]])
    jour.insert(4, "echeance_jours", 1)
    jour["echeance_jours"] = jour["echeance_jours"].astype("int32")
    jour["source"] = "previous_runs"
    jour["modele"] = MODELE
    jour["date_extraction_utc"] = extraction_utc
    return jour


emises = pd.concat([previsions_veille(s) for s in sites], ignore_index=True)
print(f"{len(emises)} prévisions de la veille, du {emises['date'].min()} au {emises['date'].max()}, "
      f"rafales renseignées sur {int(emises['wind_gusts_10m_max'].notna().sum())} lignes")

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
    "previsions_veille": int(len(emises)),
}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
