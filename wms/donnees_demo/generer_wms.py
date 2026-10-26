"""
Génère les données de démonstration du WMS à partir des commandes du site
e-commerce (base NopCommerce amazingdb), pour que les deux systèmes racontent
la même histoire : mêmes numéros de commande, mêmes SKU, expéditions cohérentes
avec les statuts de livraison du site.

  - 4 entrepôts (codes WH1 à WH4, ceux utilisés par l'ingestion météo),
  - un article WMS par produit du catalogue (sku = Product.Sku),
  - un client logistique « ECOM » (le canal du site : le WMS ne connaît pas
    le client final),
  - une commande logistique par commande payée, préparée dans l'entrepôt
    le plus proche de la région du client,
  - une expédition par commande expédiée, avec transporteur et délai réaliste,
  - un stock courant par article et par entrepôt.

La région du client vient du référentiel géographique versionné
(referentiels/referentiel_geographique.xlsx), ou du Lakehouse avec --geo lakehouse.

Le script écrit un fichier SQL (tables vidées puis rechargées) à exécuter sur
la VM avec psql, après la migration 002 :

    python generer_wms.py > wms_demo.sql
    sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -f wms_demo.sql
"""
import argparse
import json
import os
import random
import struct
import sys
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pyodbc

SERVEUR_SQL = os.environ.get("AMAZINGZONE_SQL_SERVEUR", "amazingserver.database.windows.net")
SERVEUR_LK = os.environ.get("AMAZINGZONE_POINT_SQL_FABRIC",
                            "xpuudm5uch6ezlvpconr4xjvpm-hu3xkcgnsyhe3nhhl7c42mt4xa.datawarehouse.fabric.microsoft.com")
FICHIER_GEO = Path(__file__).resolve().parents[2] / "referentiels" / "referentiel_geographique.xlsx"

ENTREPOTS = [
    ("WH1", "Entrepôt principal - Saran (Orléans)"),
    ("WH2", "Entrepôt Saint-Quentin-Fallavier (Lyon)"),
    ("WH3", "Entrepôt Lesquin (Lille)"),
    ("WH4", "Entrepôt Vitrolles (Marseille)"),
]
# Entrepôt de préparation selon la région du client
REGION_ENTREPOT = {
    "Hauts-de-France": "WH3", "Normandie": "WH3", "Grand Est": "WH2",
    "Auvergne-Rhône-Alpes": "WH2", "Bourgogne-Franche-Comté": "WH2",
    "Provence-Alpes-Côte d'Azur": "WH4", "Occitanie": "WH4", "Corse": "WH4",
    "Nouvelle-Aquitaine": "WH4",
}
EMPLACEMENTS = [("RCV-01", "RECEIVING"), ("STO-01", "STORAGE"), ("STO-02", "STORAGE"),
                ("PICK-01", "PICK"), ("PACK-01", "PACK"), ("SHP-01", "SHIPPING")]


def jeton(scope):
    donnees = urllib.parse.urlencode({
        "client_id": os.environ["AZURE_CLIENT_ID"], "client_secret": os.environ["AZURE_CLIENT_SECRET"],
        "grant_type": "client_credentials", "scope": scope}).encode()
    url = f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}/oauth2/v2.0/token"
    return json.load(urllib.request.urlopen(url, donnees))["access_token"]


def connexion(serveur, base):
    t = jeton("https://database.windows.net/.default").encode("utf-16-le")
    return pyodbc.connect(f"Driver={{ODBC Driver 18 for SQL Server}};Server={serveur};Database={base};Encrypt=yes",
                          attrs_before={1256: struct.pack(f"<I{len(t)}s", len(t), t)}, timeout=180)


def referentiel_geographique(source):
    """Départements du référentiel géographique : copie versionnée du classeur (par défaut), ou table
    referentiels.geographie du Lakehouse si le classeur de SharePoint a été modifié depuis."""
    if source == "lakehouse":
        with connexion(SERVEUR_LK, "AmazingZoneLK") as lk:
            cur = lk.cursor().execute("SELECT * FROM referentiels.geographie ORDER BY code_departement")
            entete = [c[0] for c in cur.description]
            return [SimpleNamespace(**dict(zip(entete, l))) for l in cur.fetchall()]
    feuille = openpyxl.load_workbook(FICHIER_GEO, read_only=True)["Départements"]
    entete, *lignes = feuille.iter_rows(values_only=True)
    return sorted((SimpleNamespace(**dict(zip(entete, l))) for l in lignes if l[0]),
                  key=lambda g: g.code_departement)


def departement(cp):
    if not cp:
        return None
    if cp.startswith("97"):
        return cp[:3]
    if cp.startswith("20"):
        return "2A" if cp < "20200" else "2B"
    return cp[:2]


def sql_str(v):
    return "\\N" if v is None else str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ")


def copie(table, colonnes, lignes):
    print(f"COPY {table} ({', '.join(colonnes)}) FROM stdin;")
    for l in lignes:
        print("\t".join(sql_str(v) for v in l))
    print("\\.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", choices=["fichier", "lakehouse"], default="fichier",
                    help="source du référentiel géographique (défaut : referentiels/referentiel_geographique.xlsx)")
    args = ap.parse_args()
    random.seed(2026)
    regions = {g.code_departement: g.region for g in referentiel_geographique(args.geo)}
    with connexion(SERVEUR_SQL, "amazingdb") as cn:
        cur = cn.cursor()
        produits = cur.execute("SELECT Id, Sku, Name FROM dbo.Product WHERE Sku IS NOT NULL AND Deleted = 0").fetchall()
        commandes = cur.execute("""
            SELECT o.Id, o.CustomOrderNumber, o.OrderStatusId, o.ShippingStatusId, o.PaidDateUtc, o.CreatedOnUtc,
                   o.ShippingMethod, c.ZipPostalCode
            FROM dbo.[Order] o JOIN dbo.Customer c ON c.Id = o.CustomerId
            WHERE o.PaidDateUtc IS NOT NULL OR o.OrderStatusId = 40""").fetchall()
        lignes = cur.execute("SELECT OrderId, ProductId, Quantity FROM dbo.OrderItem ORDER BY OrderId, Id").fetchall()
    sku = {p.Id: p.Sku for p in produits}
    lignes_par_commande = {}
    for l in lignes:
        lignes_par_commande.setdefault(l.OrderId, []).append(l)

    print("\\set ON_ERROR_STOP on")
    print("BEGIN;")
    print("TRUNCATE wms.shipment, wms.order_line, wms.orders, wms.inventory, wms.item, wms.customer RESTART IDENTITY CASCADE;")
    for code, nom in ENTREPOTS:
        print(f"INSERT INTO wms.warehouse(code, name) VALUES ('{code}', '{nom}') "
              f"ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name;")
    for code, typ in EMPLACEMENTS:
        print(f"INSERT INTO wms.location(warehouse_id, code, type) SELECT warehouse_id, '{code}', '{typ}' "
              f"FROM wms.warehouse ON CONFLICT (warehouse_id, code) DO NOTHING;")
    print("INSERT INTO wms.customer(code, name) VALUES ('ECOM', 'Site e-commerce Amazing Zone');")
    copie("wms.item", ["sku", "description", "uom"], [(p.Sku, p.Name, "EA") for p in produits])

    # Stock courant : réserve et emplacement de picking dans chaque entrepôt
    print("CREATE TEMP TABLE t_stock(sku text, wh text, loc text, qty numeric, res numeric);")
    copie("t_stock", ["sku", "wh", "loc", "qty", "res"],
          [(p.Sku, wh, loc, random.randint(*bornes), random.randint(0, 5))
           for p in produits for wh, _ in ENTREPOTS for loc, bornes in (("STO-01", (20, 400)), ("PICK-01", (0, 30)))])
    print("""INSERT INTO wms.inventory(item_id, location_id, qty_on_hand, qty_reserved)
             SELECT i.item_id, l.location_id, s.qty, LEAST(s.res, s.qty)
             FROM t_stock s JOIN wms.item i ON i.sku = s.sku
             JOIN wms.warehouse w ON w.code = s.wh JOIN wms.location l ON l.warehouse_id = w.warehouse_id AND l.code = s.loc;""")

    # Commandes, lignes et expéditions
    t_cmd, t_lig, t_exp = [], [], []
    for o in commandes:
        if o.OrderStatusId == 40 and random.random() < 0.5:
            continue  # annulée avant transmission au WMS
        wh = REGION_ENTREPOT.get(regions.get(departement(o.ZipPostalCode)), "WH1")
        debut = (o.PaidDateUtc or o.CreatedOnUtc) + timedelta(minutes=random.randint(2, 20))
        if o.OrderStatusId == 40:
            statut = "CANCELLED"
        elif o.ShippingStatusId in (30, 40):
            statut = "SHIPPED"
        else:
            statut = random.choice(["ALLOCATED", "PICKED", "PACKED"])
        t_cmd.append((o.CustomOrderNumber, wh, debut.strftime("%Y-%m-%d %H:%M:%S+00"), statut))
        for n, l in enumerate(lignes_par_commande.get(o.Id, []), start=1):
            if l.ProductId in sku:
                t_lig.append((o.CustomOrderNumber, n, sku[l.ProductId], l.Quantity,
                              l.Quantity if statut in ("SHIPPED", "PICKED", "PACKED") else 0))
        if statut == "SHIPPED":
            if o.ShippingMethod == "Pickup in store":
                transporteur, suivi, delai = "Retrait", None, random.randint(4, 30)
            elif o.ShippingMethod == "Next Day Air":
                transporteur, delai = "Chronopost", random.randint(2, 18)
                suivi = f"XR{random.randint(10**8, 10**9 - 1)}FR"
            else:
                transporteur = random.choices(["Colissimo", "DPD"], [65, 35])[0]
                delai = random.randint(10, 60) + (40 if debut.weekday() >= 5 else 0)
                suivi = (f"6A{random.randint(10**10, 10**11 - 1)}" if transporteur == "Colissimo"
                         else f"0{random.randint(10**12, 10**13 - 1)}")
            t_exp.append((o.CustomOrderNumber, transporteur, suivi,
                          (debut + timedelta(hours=delai)).strftime("%Y-%m-%d %H:%M:%S+00")))

    print("CREATE TEMP TABLE t_cmd(order_no text, wh text, order_date timestamptz, status text);")
    copie("t_cmd", ["order_no", "wh", "order_date", "status"], t_cmd)
    print("""INSERT INTO wms.orders(order_no, customer_id, order_date, status, warehouse_id)
             SELECT c.order_no, (SELECT customer_id FROM wms.customer WHERE code = 'ECOM'), c.order_date, c.status, w.warehouse_id
             FROM t_cmd c JOIN wms.warehouse w ON w.code = c.wh;""")
    print("CREATE TEMP TABLE t_lig(order_no text, line_no int, sku text, qty numeric, picked numeric);")
    copie("t_lig", ["order_no", "line_no", "sku", "qty", "picked"], t_lig)
    print("""INSERT INTO wms.order_line(order_id, line_no, item_id, qty_ordered, qty_picked)
             SELECT o.order_id, l.line_no, i.item_id, l.qty, l.picked
             FROM t_lig l JOIN wms.orders o ON o.order_no = l.order_no JOIN wms.item i ON i.sku = l.sku;""")
    print("CREATE TEMP TABLE t_exp(order_no text, carrier text, tracking_no text, shipped_at timestamptz);")
    copie("t_exp", ["order_no", "carrier", "tracking_no", "shipped_at"], t_exp)
    print("""INSERT INTO wms.shipment(order_id, carrier, tracking_no, shipped_at)
             SELECT o.order_id, e.carrier, e.tracking_no, e.shipped_at FROM t_exp e JOIN wms.orders o ON o.order_no = e.order_no;""")
    print("DROP TABLE IF EXISTS wms._order_no_raw;")
    print("COMMIT;")
    print("SELECT 'orders' t, count(*) FROM wms.orders UNION ALL SELECT 'order_line', count(*) FROM wms.order_line "
          "UNION ALL SELECT 'shipment', count(*) FROM wms.shipment UNION ALL SELECT 'inventory', count(*) FROM wms.inventory;")
    print(f"-- {len(t_cmd)} commandes, {len(t_lig)} lignes, {len(t_exp)} expéditions", file=sys.stderr)


if __name__ == "__main__":
    main()
