# Site e-commerce – base NopCommerce

Base Azure SQL Database `amazingdb` (serveur `amazingserver`), source du site e-commerce d'Amazing Zone,
répliquée dans Fabric par le mirroring.

## Données de démonstration

`donnees_demo/generer_commandes.py` ajoute un jeu cohérent au catalogue NopCommerce d'origine :
600 clients français générés (qui s'ajoutent aux 6 comptes du jeu NopCommerce d'origine, soit 606 au total) répartis sur les départements du référentiel géographique, environ 4 000 commandes
de janvier 2025 à octobre 2026 (saisonnalité de fin d'année, statuts de paiement et de livraison selon
l'ancienneté), et un coût d'achat pour chaque produit. Les clients générés ont une adresse en
`@demo.amazingzone.fr` ; `--purge` les supprime avec leurs commandes avant de régénérer.

```bash
python generer_commandes.py --purge   # graine fixe : le jeu obtenu est toujours le même
```

Les départements viennent de la copie versionnée du référentiel géographique,
`referentiels/referentiel_geographique.xlsx` ; `--geo lakehouse` lit à la place la table `referentiels.geographie`
du Lakehouse. Le serveur se lit dans les variables `AMAZINGZONE_SQL_SERVEUR` et `AMAZINGZONE_SQL_BASE`, le point
de terminaison SQL de Fabric (option `--geo lakehouse` seulement) dans `AMAZINGZONE_POINT_SQL_FABRIC` (voir
`.env.exemple`). L'installation du site nopCommerce
est décrite dans `installation/02-site-ecommerce-nopcommerce.md`.

Le WMS se régénère ensuite à partir de ces commandes (voir `wms/donnees_demo`).
