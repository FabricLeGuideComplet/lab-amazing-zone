"""
Déploie les éléments Fabric du lab (dossier workspaces/amazingzone) dans votre espace de travail, avec fabric-cicd.

Les valeurs propres à l'environnement de l'auteur (identifiants d'espace, de Lakehouse, de connexions, hôte
SharePoint) sont remplacées selon workspaces/amazingzone/parameter.yml : les éléments déployés sont résolus par
fabric-cicd, le reste est lu dans les variables d'environnement (fichier .env, voir .env.exemple).

Authentification : principal de service du lab (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET), membre
de l'espace avec le rôle Administrateur ou Membre, et autorisé à appeler les API Fabric par le paramètre de locataire.

    pip install fabric-cicd azure-identity
    set -a; . ./.env; set +a
    python installation/deployer_fabric.py --espace <id de l'espace>                 # sans les éléments archivés
    python installation/deployer_fabric.py --espace <id de l'espace> --avec-archives
"""
import argparse
import os
from pathlib import Path

from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, append_feature_flag, publish_all_items

DEPOT = Path(__file__).resolve().parent.parent / "workspaces" / "amazingzone"

# Types d'éléments présents dans le dépôt et pris en charge par fabric-cicd. L'application d'organisation
# (OrgApp) ne l'est pas : elle se recrée à la main (installation/07-fabric-espaces-et-elements.md).
TYPES = ["Lakehouse", "Warehouse", "Eventhouse", "KQLDatabase", "Notebook", "CopyJob", "Dataflow",
         "DataPipeline", "DataBuildToolJob", "SemanticModel", "Report", "Eventstream", "KQLQueryset",
         "KQLDashboard", "Reflex", "GraphQLApi", "UserDataFunction"]

# Éléments du dossier « 9 - Archives », conservés pour les démonstrations du livre
ARCHIVES = r"^(Ingestion - NopCommerce \(remplacée par le mirroring\)|Ingestion - WMS par métadonnées" \
           r"|Optimisation - Table sensors|Test_RTDashboard)$"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--espace", required=True, help="identifiant de l'espace de travail cible")
    ap.add_argument("--avec-archives", action="store_true", help="déployer aussi les éléments archivés")
    args = ap.parse_args()

    append_feature_flag("enable_environment_variable_replacement")
    # Raccourcis ecommerce du Lakehouse vers la base mirrorée : le mirroring doit exister avant le déploiement
    append_feature_flag("enable_experimental_features")
    append_feature_flag("enable_shortcut_publish")

    credentiel = ClientSecretCredential(os.environ["AZURE_TENANT_ID"], os.environ["AZURE_CLIENT_ID"],
                                        os.environ["AZURE_CLIENT_SECRET"])
    espace = FabricWorkspace(
        workspace_id=args.espace,
        environment="LAB",
        repository_directory=str(DEPOT),
        item_type_in_scope=TYPES,
        token_credential=credentiel,
    )
    publish_all_items(espace, item_name_exclude_regex=None if args.avec_archives else ARCHIVES)


if __name__ == "__main__":
    main()
