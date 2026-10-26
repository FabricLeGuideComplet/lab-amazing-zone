"""Simulateur du module temps réel du WMS d'Amazing Zone.

Émet des événements logistiques (réception, mise à jour de stock, préparation validée, expédition) vers le point
de terminaison personnalisé (custom endpoint) de l'Eventstream « Flux - Événements WMS », au format JSON, par le protocole
Event Hub. Il remplace, dans le lab, le module Python du WMS décrit au chapitre 2 du livre.

Chaîne de connexion :
    - soit la variable WMS_EVENTSTREAM_CS (Eventstream > source WMSEvent > Event Hub > Keys) ;
    - soit, à défaut, le principal de service du lab (.env : AZURE_TENANT_ID, AZURE_CLIENT_ID,
      AZURE_CLIENT_SECRET), qui la lit au travers de l'API Fabric (sources/{id}/connection) ;
      l'Eventstream est désigné par FABRIC_ESPACE_ID, WMS_EVENTSTREAM_ID et WMS_EVENTSTREAM_SOURCE_ID.

Usage :
    pip install azure-eventhub
    python simulateur_evenements.py --par-minute 60 --duree 10      # 60 événements/min pendant 10 minutes
    python simulateur_evenements.py --une-salve 20                    # 20 événements puis arrêt
"""
import argparse
import json
import os
import random
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

from azure.eventhub import EventData, EventHubProducerClient

ESPACE = os.environ.get('FABRIC_ESPACE_ID', '0875373d-96cd-4d0e-b4e7-5fc5cd327cb8')               # AmazingZone - Dev - Marie
EVENTSTREAM = os.environ.get('WMS_EVENTSTREAM_ID', '75e869b0-3e3c-438e-9871-9b91482f39a7')        # Flux - Événements WMS
SOURCE = os.environ.get('WMS_EVENTSTREAM_SOURCE_ID', '3e02f1ab-b89d-41a8-8516-9c8c8ec0b854')     # WMSEvent (custom endpoint)

# Référentiel du WMS (schéma wms) : entrepôts, emplacements et articles de démonstration
ENTREPOTS = ['WH1', 'WH2', 'WH3', 'WH4']
EMPLACEMENTS = {'RECEPTION': 'RCV-01', 'STOCKAGE': ['STO-01', 'STO-02'], 'PREPARATION': 'PICK-01', 'EXPEDITION': 'SHP-01'}
ARTICLES = ['SKU-0001', 'SKU-0002', 'SKU-0003', 'SKU-0004', 'SKU-0005']
TRANSPORTEURS = ['Colissimo', 'Chronopost', 'DPD', 'GLS']
# Fréquence relative des types d'événements : l'activité d'un entrepôt est dominée par les mouvements de stock
TYPES = [('STOCK_UPDATE', 5), ('PICKING_VALIDATED', 3), ('SHIPMENT', 2), ('RECEPTION', 1)]


def chaine_de_connexion():
    cs = os.environ.get('WMS_EVENTSTREAM_CS')
    if cs:
        return cs
    t, c, s = (os.environ[k] for k in ('AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET'))
    corps = urllib.parse.urlencode({'grant_type': 'client_credentials', 'client_id': c, 'client_secret': s,
                                    'scope': 'https://api.fabric.microsoft.com/.default'}).encode()
    jeton = json.load(urllib.request.urlopen(f'https://login.microsoftonline.com/{t}/oauth2/v2.0/token', corps))
    url = (f'https://api.fabric.microsoft.com/v1/workspaces/{ESPACE}/eventstreams/{EVENTSTREAM}'
           f'/sources/{SOURCE}/connection')
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + jeton['access_token']})
    return json.load(urllib.request.urlopen(req))['accessKeys']['primaryConnectionString']


def evenement():
    type_evt = random.choices([t for t, _ in TYPES], weights=[p for _, p in TYPES])[0]
    entrepot = random.choice(ENTREPOTS)
    article = random.choice(ARTICLES)
    evt = {
        'eventId': str(uuid.uuid4()),
        'eventType': type_evt,
        'eventTime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
        'warehouse': entrepot,
        'sku': article,
        'orderNo': None,
        'location': None,
        'quantity': None,
        'carrier': None,
    }
    if type_evt == 'RECEPTION':
        evt.update(location=EMPLACEMENTS['RECEPTION'], quantity=random.choice([24, 48, 96, 120]))
    elif type_evt == 'STOCK_UPDATE':
        evt.update(location=random.choice(EMPLACEMENTS['STOCKAGE']), quantity=random.randint(-12, 30))
    elif type_evt == 'PICKING_VALIDATED':
        evt.update(location=EMPLACEMENTS['PREPARATION'], quantity=random.randint(1, 6),
                   orderNo=f'ORD{random.randint(3950000, 3999999)}')
    else:  # SHIPMENT
        evt.update(location=EMPLACEMENTS['EXPEDITION'], quantity=random.randint(1, 6),
                   orderNo=f'ORD{random.randint(3950000, 3999999)}', carrier=random.choice(TRANSPORTEURS))
    return evt


def envoyer(producteur, nombre):
    lot = producteur.create_batch()
    for _ in range(nombre):
        lot.add(EventData(json.dumps(evenement())))
    producteur.send_batch(lot)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--par-minute', type=int, default=60, help='événements émis par minute')
    p.add_argument('--duree', type=float, default=5, help='durée en minutes')
    p.add_argument('--une-salve', type=int, help='émet ce nombre d\'événements en une fois, puis s\'arrête')
    a = p.parse_args()

    producteur = EventHubProducerClient.from_connection_string(chaine_de_connexion())
    with producteur:
        if a.une_salve:
            envoyer(producteur, a.une_salve)
            print(f'{a.une_salve} événement(s) envoyé(s)')
            return
        fin, total = time.time() + a.duree * 60, 0
        while time.time() < fin:
            # envoi toutes les 5 secondes, pour un débit moyen de --par-minute
            nombre = max(1, round(random.gauss(a.par_minute / 12, a.par_minute / 48)))
            envoyer(producteur, nombre)
            total += nombre
            print(f'{datetime.now():%H:%M:%S}  {nombre:3d} événement(s), {total} au total', flush=True)
            time.sleep(5)


if __name__ == '__main__':
    main()
