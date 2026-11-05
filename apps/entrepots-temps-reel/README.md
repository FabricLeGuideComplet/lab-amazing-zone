# Entrepôts en temps réel (Fabric App)

Application web d'Amazing Zone hébergée dans Fabric (élément « Suivi_entrepots_temps_reel » de l'espace
AmazingZone - Dev - Marie), réalisée pour le chapitre consacré au temps réel. Elle affiche, pour chacun des quatre
entrepôts, l'activité de la dernière heure et le temps écoulé depuis le dernier événement du WMS. L'écran est relu
toutes les 30 secondes : rien n'est poussé vers l'application.

L'application ne lit pas l'Eventhouse directement. Le connecteur `kusto` des Fabric Apps est retenu dans la version
publiée du SDK (1.36.2), et le service refuse de l'exécuter même déployé avec la version expérimentale. Elle passe
donc par le point de terminaison SQL du Lakehouse :

1. Disponibilité OneLake activée sur la table KQL `wms_evenements` (base AmazingZoneEH), délai d'écriture de
   5 minutes :
   `.alter table wms_evenements policy mirroring dataformat=parquet with (IsEnabled=true, Backfill=true, TargetLatencyInMinutes=5)`
2. Raccourci OneLake `wms.evenements` dans le Lakehouse AmazingZoneLK, vers `Tables/wms_evenements` de la base KQL.
3. Vue `api.sante_entrepots` dans le point de terminaison SQL du Lakehouse (`sql/sante_entrepots.sql`).
4. Connecteur `fabric-sqlanalytics` (`evenementswms`), en lecture seule et en délégation : chaque utilisateur lit
   avec ses propres droits, y compris sur la base KQL visée par le raccourci.

Conséquence : l'écran a quelques minutes de retard sur l'Eventhouse (délai d'écriture dans OneLake, puis
synchronisation du point de terminaison SQL). L'application affiche ce retard, et la vue mesure le silence d'un
entrepôt par rapport au dernier événement copié, pas à l'heure courante.

- Code : React + Vite + TypeScript, SDK Rayfin 1.36.2.
- `rayfin/connectors/evenementswms/SanteEntrepots.ts` est écrit à la main : la découverte du connecteur ne liste
  que les tables du Lakehouse, pas ses vues.
- Pas de base de données propre à l'application (`services.data.enabled: false`).
- Déploiement : `npx rayfin login`, puis
  `npx rayfin up --workspace-id <espace> --item-name Suivi_entrepots_temps_reel`.
  `rayfin/.env` et `rayfin/.deployments.json` ne sont pas versionnés.
