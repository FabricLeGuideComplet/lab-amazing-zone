"""
Déploiement des éléments Fabric d'Amazing Zone (dossier workspaces/amazingzone) vers l'espace d'intégration,
de test ou de production, avec fabric-cicd (chapitre 10 « Industrialiser »).

    pip install fabric-cicd==1.4.0 azure-identity
    python deploiement/deployer.py --environnement INTEGRATION|TEST|PROD [--simulation]

Authentification : principal de service SP-Fabric-AmazingZone, administrateur des trois espaces par le groupe
dp-equipedata. Dans Azure Pipelines, par la connexion de service « fabric-deploiement » (fédération d'identité de
charge de travail, sans secret) et Azure CLI ; sur un poste, par AZURE_TENANT_ID, AZURE_CLIENT_ID et
AZURE_CLIENT_SECRET.

Variables d'environnement attendues (fichier .env sur un poste, variables du pipeline dans Azure DevOps ; voir
.env.exemple et installation/11-industrialisation.md) :
  - FABRIC_ESPACE_INTEGRATION_ID, FABRIC_ESPACE_TEST_ID, FABRIC_ESPACE_PROD_ID : les trois espaces cibles ;
  - CONNEXION_SHAREPOINT_FINANCE : connexion « SharePoint - Finance (SP AmazingZone) », liée au modèle après
    publication ;
  - toutes les variables $ENV: de workspaces/amazingzone/parameter.yml (connexions, coffre, SharePoint, base
    mirrorée, destinataire des alertes, locataire et principal de service).

Les identifiants propres à chaque espace sont remplacés selon workspaces/amazingzone/parameter.yml.
"""
import argparse
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
import urllib.request
from pathlib import Path

from azure.identity import AzureCliCredential, ClientSecretCredential
from fabric_cicd import FabricWorkspace, append_feature_flag, publish_all_items

RACINE = Path(__file__).resolve().parent.parent
DEPOT = RACINE / "workspaces" / "amazingzone"
SCRIPT_KQL = RACINE / "eventhouse" / "amazingzoneeh.kql"
# Marqueurs des tables externes de eventhouse/amazingzoneeh.kql, remplacés par l'espace et le Warehouse cibles
ESPACE_SOURCE, WAREHOUSE_SOURCE = "<ID_ESPACE>", "<ID_WAREHOUSE_AMAZINGZONEWH>"

# Variable d'environnement qui porte l'identifiant de l'espace cible de chaque environnement
ESPACES = {
    "INTEGRATION": "FABRIC_ESPACE_INTEGRATION_ID",   # AmazingZone - Dev
    "TEST": "FABRIC_ESPACE_TEST_ID",                 # AmazingZone - Test
    "PROD": "FABRIC_ESPACE_PROD_ID",                 # AmazingZone - Prod
}

TYPES = ["Lakehouse", "Warehouse", "Eventhouse", "KQLDatabase", "Notebook", "CopyJob", "Dataflow",
         "DataPipeline", "DataBuildToolJob", "SemanticModel", "Report", "Eventstream", "KQLQueryset",
         "KQLDashboard", "Reflex", "GraphQLApi", "UserDataFunction"]

# Jamais déployés : éléments que Fabric crée lui-même dans l'espace de développement (lien Dataverse, préparation
# des Dataflows), s'ils ont été validés dans le dépôt, et éléments archivés du dossier « 9 - Archives ».
EXCLUS_PARTOUT = [r"dataverse_.*", r"Staging(Lakehouse|Warehouse)ForDataflows_.*",
                  r"Ingestion - NopCommerce \(remplacée par le mirroring\)", r"Ingestion - WMS par métadonnées",
                  r"Optimisation - Table sensors", r"Test_RTDashboard", r"Analyse des journaux du site",
                  # le flux des journaux lit l'Event Hub avec le groupe de consommateurs de l'espace de développement
                  r"Flux - Journaux du site"]

# Hors intégration : ce qui ne doit pas tourner en double. Les Activator surveilleraient des bases vides et
# alerteraient en boucle ; le contrôle des tenant settings est planifié une seule fois.
EXCLUS_HORS_INTEGRATION = [r"Alerte - .*", r"Contrôle - Tenant settings"]


def api_fabric(credentiel, chemin):
    jeton = credentiel.get_token("https://api.fabric.microsoft.com/.default").token
    req = urllib.request.Request("https://api.fabric.microsoft.com/v1/" + chemin,
                                 headers={"Authorization": "Bearer " + jeton})
    return json.load(urllib.request.urlopen(req))


def completer_base_kql(credentiel, espace_id):
    """Action après déploiement : la définition Git de la base KQL ne contient ni les tables externes ni la
    disponibilité de wms_evenements dans OneLake. On les rejoue depuis eventhouse/amazingzoneeh.kql, en
    pointant les tables externes vers le Warehouse de l'espace cible."""
    elements = api_fabric(credentiel, f"workspaces/{espace_id}/items")["value"]
    warehouse = next(e["id"] for e in elements if e["type"] == "Warehouse" and e["displayName"] == "AmazingZoneWH")
    eventhouse = next(e["id"] for e in elements if e["type"] == "Eventhouse" and e["displayName"] == "AmazingZoneEH")
    uri = api_fabric(credentiel, f"workspaces/{espace_id}/eventhouses/{eventhouse}")["properties"]["queryServiceUri"]
    blocs = [b.strip() for b in SCRIPT_KQL.read_text(encoding="utf-8").split("\n\n")]
    commandes = [b for b in blocs if b.startswith(".create-or-alter external table")
                 or re.match(r"\.alter table wms_evenements policy mirroring", b)]
    jeton = credentiel.get_token(uri + "/.default").token
    for commande in commandes:
        commande = commande.replace(ESPACE_SOURCE, espace_id).replace(WAREHOUSE_SOURCE, warehouse)
        corps = json.dumps({"db": "AmazingZoneEH", "csl": commande}).encode()
        req = urllib.request.Request(uri + "/v1/rest/mgmt", data=corps, method="POST",
                                     headers={"Authorization": "Bearer " + jeton, "Content-Type": "application/json"})
        urllib.request.urlopen(req).read()
        print("Base KQL :", commande.splitlines()[0][:90], flush=True)


FLUX_WMS = "Flux - Événements WMS.Eventstream"


def destination_activator(copie, retirer):
    """L'Eventstream du WMS envoie ses événements à l'Activator « Alerte - Activité des entrepôts », qui le lit en
    retour : dépendance circulaire, impossible à créer d'un coup. On retire la destination Activator de la copie,
    puis on la remet une fois l'Activator publié."""
    fichier = next(copie.rglob(FLUX_WMS + "/eventstream.json"))
    sauvegarde = copie.parent / "eventstream_wms_complet.json"   # hors du dossier : fabric-cicd publie tout ce qu'il contient
    if retirer:
        definition = json.loads(fichier.read_text(encoding="utf-8"))
        sauvegarde.write_text(json.dumps(definition, ensure_ascii=False), encoding="utf-8")
        definition["destinations"] = [d for d in definition["destinations"] if d.get("type") != "Activator"]
        fichier.write_text(json.dumps(definition, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        fichier.write_text(sauvegarde.read_text(encoding="utf-8"), encoding="utf-8")


def precreer_eventstreams(credentiel, espace_id, copie, exclus):
    """L'API refuse de créer un Eventstream dont le nom contient une espace (« Artifact display name is not
    valid »), mais accepte de le renommer ensuite, comme l'interface. On crée donc les Eventstreams absents de la
    cible sous un nom sans espace ni accent, puis on les renomme ; fabric-cicd les retrouve alors par leur nom."""
    jeton = credentiel.get_token("https://api.fabric.microsoft.com/.default").token
    entetes = {"Authorization": "Bearer " + jeton, "Content-Type": "application/json"}
    existants = {e["displayName"] for e in api_fabric(credentiel, f"workspaces/{espace_id}/items?type=Eventstream")["value"]}
    for dossier in copie.rglob("*.Eventstream"):
        nom = json.loads((dossier / ".platform").read_text(encoding="utf-8-sig"))["metadata"]["displayName"]
        if nom in existants or " " not in nom or re.match(r"^(" + "|".join(exclus) + r")$", nom):
            continue
        provisoire = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().replace(" ", "")
        req = urllib.request.Request(f"https://api.fabric.microsoft.com/v1/workspaces/{espace_id}/eventstreams",
                                     data=json.dumps({"displayName": provisoire}).encode(), method="POST",
                                     headers=entetes)
        urllib.request.urlopen(req).read()
        for _ in range(30):   # création asynchrone
            trouves = [e for e in api_fabric(credentiel, f"workspaces/{espace_id}/items?type=Eventstream")["value"]
                       if e["displayName"] == provisoire]
            if trouves:
                break
            time.sleep(10)
        req = urllib.request.Request(f"https://api.fabric.microsoft.com/v1/workspaces/{espace_id}/items/{trouves[0]['id']}",
                                     data=json.dumps({"displayName": nom}).encode(), method="PATCH", headers=entetes)
        urllib.request.urlopen(req).read()
        print(f"Eventstream créé sous le nom « {provisoire} », puis renommé « {nom} »", flush=True)


def lier_modele(credentiel, espace_id):
    """Lie la source SharePoint (table Budget) du modèle « Ventes et logistique » à la connexion partagée.
    Sans liaison, toute mise à jour du modèle échoue faute d'identifiants. Le paramètre semantic_model_binding
    de fabric-cicd 1.4.0 ne convient pas : il envoie le chemin de la connexion (le site) et non celui de la
    source du modèle (le classeur), ce que l'API refuse."""
    connexion_sharepoint = os.environ["CONNEXION_SHAREPOINT_FINANCE"]   # SharePoint - Finance (SP AmazingZone)
    jeton = credentiel.get_token("https://api.fabric.microsoft.com/.default").token
    modeles = api_fabric(credentiel, f"workspaces/{espace_id}/items?type=SemanticModel")["value"]
    modele = next(m["id"] for m in modeles if m["displayName"] == "Ventes et logistique")
    for source in api_fabric(credentiel, f"workspaces/{espace_id}/items/{modele}/connections")["value"]:
        details = source["connectionDetails"]
        if details["type"] != "Web" or source.get("id") == connexion_sharepoint:
            continue
        corps = json.dumps({"connectionBinding": {"id": connexion_sharepoint, "connectivityType": "ShareableCloud",
                                                  "connectionDetails": details}}).encode()
        req = urllib.request.Request(
            f"https://api.fabric.microsoft.com/v1/workspaces/{espace_id}/semanticModels/{modele}/bindConnection",
            data=corps, method="POST", headers={"Authorization": "Bearer " + jeton, "Content-Type": "application/json"})
        urllib.request.urlopen(req).read()
        print("Modèle « Ventes et logistique » lié à SharePoint - Finance (SP AmazingZone)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--environnement", required=True, choices=sorted(ESPACES))
    ap.add_argument("--simulation", action="store_true", help="n'affiche que la liste des éléments à publier")
    args = ap.parse_args()

    espace_id = os.environ[ESPACES[args.environnement]]
    exclus = EXCLUS_PARTOUT + ([] if args.environnement == "INTEGRATION" else EXCLUS_HORS_INTEGRATION)

    # parameter.yml lit dans les variables d'environnement ce qui vit hors de l'espace ($ENV:NOM)
    append_feature_flag("enable_environment_variable_replacement")
    append_feature_flag("enable_experimental_features")
    append_feature_flag("enable_shortcut_publish")
    append_feature_flag("enable_items_to_include")

    # Dans Azure Pipelines, la tâche AzureCLI@2 connecte Azure CLI au principal de service par fédération
    # d'identité de charge de travail (aucun secret stocké) ; sur un poste, le secret du fichier .env.
    if os.environ.get("AZURE_CLIENT_SECRET"):
        credentiel = ClientSecretCredential(os.environ["AZURE_TENANT_ID"], os.environ["AZURE_CLIENT_ID"],
                                            os.environ["AZURE_CLIENT_SECRET"])
    else:
        credentiel = AzureCliCredential()
    # La base KQL se cite elle-même dans son ensemble de requêtes intégré, par son identifiant logique : sur un
    # espace vide, fabric-cicd ne peut pas la créer (« referenced item is not yet deployed »). On déploie depuis
    # une copie du dossier sans ce fichier ; l'ensemble de requêtes autonome garde les requêtes.
    copie = Path(tempfile.mkdtemp()) / "amazingzone"
    shutil.copytree(DEPOT, copie)
    for f in copie.rglob("EmbeddedRealTimeQueryset.json"):
        f.unlink()
    # L'interface et Git acceptent une description d'élément de plus de 256 caractères, l'API de création non.
    for f in copie.rglob(".platform"):
        plateforme = json.loads(f.read_text(encoding="utf-8-sig"))
        description = plateforme["metadata"].get("description", "")
        if len(description) > 256:
            plateforme["metadata"]["description"] = description[:255] + "…"
            f.write_text(json.dumps(plateforme, ensure_ascii=False, indent=2), encoding="utf-8")
    def espace():
        # fabric-cicd lit les fichiers à la création de l'objet : un objet neuf par phase, après chaque retouche
        # de la copie (et sans le filtre items_to_include, qui reste attaché à l'objet d'un appel à l'autre).
        return FabricWorkspace(workspace_id=espace_id, environment=args.environnement,
                               repository_directory=str(copie), item_type_in_scope=TYPES,
                               token_credential=credentiel)

    if args.simulation:
        for type_, elements in sorted(espace().repository_items.items()):
            print(type_, sorted(elements))
        return
    # Ordre imposé à la main (fabric-cicd ne prend pas en charge les plans de déploiement) :
    # 1. l'Eventhouse et sa base KQL d'abord, parce que le raccourci wms.evenements du Lakehouse pointe vers elle
    #    et que fabric-cicd publie les raccourcis juste après le Lakehouse ; le Warehouse avec eux, parce que les
    #    tables externes de la base KQL pointent vers lui ;
    publish_all_items(espace(), items_to_include=["AmazingZoneEH.Eventhouse", "AmazingZoneEH.KQLDatabase",
                                                  "AmazingZoneWH.Warehouse"])
    # 2. action après déploiement : tables externes et disponibilité dans OneLake, absentes de la définition Git ;
    completer_base_kql(credentiel, espace_id)
    # 3. tout le reste sauf les Activator, avec un Eventstream du WMS privé de sa destination Activator, et des
    #    Eventstreams créés à l'avance (leur nom contient des espaces) ;
    destination_activator(copie, retirer=True)
    precreer_eventstreams(credentiel, espace_id, copie, exclus)
    publish_all_items(espace(), item_name_exclude_regex=r"^(" + "|".join(exclus + [r"Alerte - .*", r"API_Stock_disponible"]) + r")$")
    # 4. action après déploiement : liaison de la table Budget du modèle à la connexion SharePoint ;
    lier_modele(credentiel, espace_id)
    # 5. en intégration seulement, les Activator, puis l'Eventstream du WMS complet.
    if args.environnement == "INTEGRATION":
        alertes = ["Alerte - Disponibilité du site.Reflex", "Alerte - Activité des entrepôts.Reflex"]
        publish_all_items(espace(), items_to_include=alertes)
        destination_activator(copie, retirer=False)
        # la mise à jour précédente de l'Eventstream est asynchrone : « Please wait until the previous operation
        # is completed before initiating the new call » si l'on enchaîne trop vite
        for essai in range(5):
            try:
                publish_all_items(espace(), items_to_include=[FLUX_WMS])
                break
            except Exception:   # noqa: BLE001
                if essai == 4:
                    raise
                time.sleep(30)
    # 6. l'API GraphQL en dernier : elle expose api.stock_disponible, une table que le job dbt construit. Sur un
    #    espace neuf, le Warehouse déployé n'est qu'une coquille : l'API ne se publie qu'après une première
    #    exécution de la chaîne (ingestion puis transformation).
    try:
        publish_all_items(espace(), items_to_include=["API_Stock_disponible.GraphQLApi"])
    except Exception as erreur:   # noqa: BLE001
        print(f"API GraphQL non publiée ({erreur}) : lancer la chaîne une première fois, puis redéployer.", flush=True)


if __name__ == "__main__":
    main()
