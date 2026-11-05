# Module temps réel du WMS (simulateur)

`simulateur_evenements.py` émet les événements logistiques du WMS d'Amazing Zone (réception, mise à jour de stock,
préparation validée, expédition) vers le point de terminaison personnalisé `WMSEvent` de l'Eventstream
« Flux - Événements WMS », au format JSON et par le protocole Event Hub. Il tient lieu, dans le lab, du module Python du WMS
décrit au chapitre 2 du livre.

```bash
pip install azure-eventhub
set -a; . ./.env; set +a            # principal de service du lab et identifiants de l'Eventstream (voir .env.exemple)
python wms/temps_reel/simulateur_evenements.py --par-minute 60 --duree 10
python wms/temps_reel/simulateur_evenements.py --par-minute 60 --duree 30 --sans-entrepot WH3   # panne de WH3
```

Les événements portent sur les couples article × entrepôt réellement stockés dans les données de démonstration du WMS
(`wms/donnees_demo/wms_demo.sql`), avec des quantités qui équilibrent réceptions et expéditions : le stock en temps réel
calculé dans l'Eventhouse oscille autour de la photo du WMS. `--sans-entrepot` simule la panne d'un entrepôt, qui n'émet
plus rien, pour tester les alertes de silence (Activator, agent opérationnel, Fabric App) du chapitre 8.

Format d'un événement :

```json
{"eventId": "…", "eventType": "PICKING_VALIDATED", "eventTime": "2026-10-17T14:02:11.512+00:00",
 "warehouse": "WH1", "sku": "PG_CR_100", "orderNo": "ORD3961245", "location": "PICK-01", "quantity": 4, "carrier": null}
```
