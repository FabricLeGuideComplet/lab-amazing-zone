# Référentiels Excel

Fichiers de référence chargés par le Dataflow Gen2 « Ingestion - Referentiels Excel » vers le schéma `referentiels` du Lakehouse `AmazingZoneLK`.
La version faisant foi est celle déposée sur SharePoint ; ce dossier en garde une copie versionnée.

| Fichier | Emplacement SharePoint | Table Lakehouse |
|---|---|---|
| `referentiel_geographique.xlsx` (feuille `Départements`) | `sites/Finance/Documents partages/Referentiels/` | `referentiels.geographie` |
| `taux_de_change_vs_eur_2019_2026.xlsx` (feuille `Taux de change vs EUR`, structure décrite dans `installation/04-sharepoint-referentiels.md`) | `sites/Finance/Documents partages/Taux de change/` | `referentiels.taux_change` |
| `budget_ventes_2026.xlsx` (feuille `Budget`) | `sites/Finance/Documents partages/` (racine de la bibliothèque) | table `Budget` (Import) du modèle sémantique « Ventes et logistique », chapitre 6 : 84 lignes (un mois × un univers de produits), 800 000 € |

Colonnes du référentiel géographique : `code_departement`, `departement`, `chef_lieu_departement`, `code_region`, `region`, `chef_lieu_region`, `outre_mer` (101 départements, régions 2016).
