# Suivi des retards d'expédition (Fabric App)

Application web d'Amazing Zone hébergée dans Fabric (élément « Suivi_retards_expedition », dossier « 4 - Restitution »
de l'espace AmazingZone - Dev - Marie). Chaque chef d'entrepôt y retrouve les commandes expédiées au-delà de 24 heures
sur les quatorze derniers jours, lues dans le modèle sémantique « Ventes et logistique » (connecteur
`venteslogistique`, requête DAX `rayfin/retards.dax`), et y saisit la cause du retard (entité `CauseRetard`, stockée
dans la base SQL de l'application, table `dbo.CauseRetards`).

- Code : React + Vite + TypeScript, SDK Rayfin 1.36.2 (versions épinglées, voir `package.json`).
- Déploiement : `npx rayfin login --tenant <tenant>` puis `npx rayfin up --workspace-id <espace> --item-name Suivi_retards_expedition`.
- L'élément Fabric App n'est pas pris en charge par l'intégration Git de l'espace de travail : ce dossier est la seule
  source de vérité du code. `rayfin/.env` et `rayfin/.deployments.json` ne sont pas versionnés.
