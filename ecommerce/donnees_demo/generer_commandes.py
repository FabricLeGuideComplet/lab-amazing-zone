"""
Génère un jeu de données de démonstration cohérent dans la base NopCommerce
(Azure SQL Database amazingdb) : clients français, commandes sur 22 mois avec
saisonnalité, lignes de commande, coûts produits.

Les clients sont répartis sur les départements du référentiel géographique
(referentiels.geographie, chargé par le Dataflow « Ingestion - Referentiels Excel »), afin que la
géographie se rapproche ensuite sans perte dans les couches Silver et Gold.

Le script est rejouable : il ne touche pas aux clients et commandes existants
(ceux du jeu NopCommerce d'origine) et n'insère que des clients dont l'adresse
e-mail se termine par @demo.amazingzone.fr. L'option --purge supprime d'abord
les données générées par une exécution précédente.

Authentification : principal de service du lab (variables AZURE_TENANT_ID,
AZURE_CLIENT_ID, AZURE_CLIENT_SECRET), qui est db_owner de la base.

    python generer_commandes.py [--purge] [--clients 600] [--graine 2026]
"""
import argparse
import json
import os
import random
import struct
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

import pyodbc

SERVEUR_SQL = os.environ.get("AMAZINGZONE_SQL_SERVEUR", "amazingserver.database.windows.net")
BASE_SQL = os.environ.get("AMAZINGZONE_SQL_BASE", "amazingdb")
# Point de terminaison SQL du Lakehouse AmazingZoneLK (lecture du référentiel géographique)
SERVEUR_LK = os.environ.get("AMAZINGZONE_POINT_SQL_FABRIC",
                            "xpuudm5uch6ezlvpconr4xjvpm-hu3xkcgnsyhe3nhhl7c42mt4xa.datawarehouse.fabric.microsoft.com")
BASE_LK = "AmazingZoneLK"
DOMAINE = "demo.amazingzone.fr"

DEBUT = datetime(2025, 1, 1)
FIN = datetime(2026, 10, 16)

# Poids des mois (saisonnalité d'un e-commerce de produits numériques)
SAISON = {1: 0.8, 2: 0.75, 3: 0.85, 4: 0.85, 5: 0.9, 6: 0.85, 7: 0.7, 8: 0.65,
          9: 0.95, 10: 1.0, 11: 1.8, 12: 2.0}
# Départements les plus peuplés, surpondérés
GRANDS_DEPARTEMENTS = {"75": 6, "13": 5, "59": 6, "69": 5, "92": 4, "93": 4, "33": 4,
                       "31": 3, "44": 3, "06": 3, "67": 3, "34": 3, "35": 3, "76": 3,
                       "94": 3, "78": 3, "91": 3, "95": 3, "62": 3, "38": 3}
PRENOMS = ["Camille", "Léa", "Manon", "Chloé", "Emma", "Inès", "Jade", "Louise", "Sarah",
           "Julie", "Lucas", "Hugo", "Louis", "Nathan", "Gabriel", "Jules", "Arthur",
           "Thomas", "Maxime", "Antoine", "Paul", "Clément", "Alice", "Zoé", "Anaïs"]
NOMS = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand",
        "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David",
        "Bertrand", "Roux", "Vincent", "Fournier", "Morel", "Girard", "André", "Mercier",
        "Dupont", "Lambert", "Bonnet", "François", "Martinez", "Legrand"]
TRANSPORTS = [("Ground", 0.7), ("Next Day Air", 0.25), ("Pickup in store", 0.05)]
PAIEMENTS = [("Payments.CreditCard", 0.7), ("Payments.PayPal", 0.25), ("Payments.CheckMoneyOrder", 0.05)]


def jeton(scope):
    donnees = urllib.parse.urlencode({
        "client_id": os.environ["AZURE_CLIENT_ID"],
        "client_secret": os.environ["AZURE_CLIENT_SECRET"],
        "grant_type": "client_credentials", "scope": scope}).encode()
    url = f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}/oauth2/v2.0/token"
    return json.load(urllib.request.urlopen(url, donnees))["access_token"]


def connexion(serveur, base):
    t = jeton("https://database.windows.net/.default").encode("utf-16-le")
    attrs = {1256: struct.pack(f"<I{len(t)}s", len(t), t)}
    return pyodbc.connect(f"Driver={{ODBC Driver 18 for SQL Server}};Server={serveur};"
                          f"Database={base};Encrypt=yes", attrs_before=attrs, timeout=180)


def tirage(options):
    r, cumul = random.random(), 0.0
    for valeur, poids in options:
        cumul += poids
        if r <= cumul:
            return valeur
    return options[-1][0]


def date_aleatoire(debut, fin):
    """Date entre debut et fin, pondérée par la saisonnalité mensuelle."""
    while True:
        d = debut + timedelta(seconds=random.randint(0, int((fin - debut).total_seconds())))
        if random.random() < SAISON[d.month] / 2.0:
            # Activité plus forte en soirée
            heure = random.choices(range(24), weights=[1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 5, 5,
                                                       6, 5, 5, 5, 5, 6, 7, 8, 9, 8, 5, 2])[0]
            return d.replace(hour=heure, minute=random.randint(0, 59), second=random.randint(0, 59))


def code_postal(departement):
    """Code postal plausible pour un département (Corse et outre-mer compris)."""
    if departement in ("2A", "2B"):
        return f"20{0 if departement == '2A' else 2}{random.randint(0, 9)}0"
    if len(departement) == 3:
        return f"{departement}{random.randint(0, 9)}0"
    return f"{departement}{random.randint(0, 9)}{random.choice(['00', '10', '20', '50'])}"


def purger(cur):
    cur.execute(f"""
        DELETE oi FROM dbo.OrderItem oi JOIN dbo.[Order] o ON o.Id = oi.OrderId
            JOIN dbo.Customer c ON c.Id = o.CustomerId WHERE c.Email LIKE '%@{DOMAINE}';
        DELETE o FROM dbo.[Order] o JOIN dbo.Customer c ON c.Id = o.CustomerId WHERE c.Email LIKE '%@{DOMAINE}';
        DELETE FROM dbo.Customer_CustomerRole_Mapping WHERE Customer_Id IN (SELECT Id FROM dbo.Customer WHERE Email LIKE '%@{DOMAINE}');
        DELETE FROM dbo.CustomerAddresses WHERE Customer_Id IN (SELECT Id FROM dbo.Customer WHERE Email LIKE '%@{DOMAINE}');
        DELETE FROM dbo.Customer WHERE Email LIKE '%@{DOMAINE}';
        DELETE FROM dbo.Address WHERE Email LIKE '%@{DOMAINE}';""")
    print("Données générées précédemment supprimées.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--purge", action="store_true")
    ap.add_argument("--clients", type=int, default=600)
    ap.add_argument("--graine", type=int, default=2026)
    args = ap.parse_args()
    random.seed(args.graine)

    # Référentiel géographique (départements) depuis le Lakehouse
    with connexion(SERVEUR_LK, BASE_LK) as lk:
        geo = lk.cursor().execute(
            "SELECT code_departement, chef_lieu_departement FROM referentiels.geographie ORDER BY code_departement").fetchall()
    poids_geo = [GRANDS_DEPARTEMENTS.get(g.code_departement, 1) for g in geo]

    cn = connexion(SERVEUR_SQL, BASE_SQL)
    cur = cn.cursor()
    if args.purge:
        purger(cur)
        cn.commit()

    france = cur.execute("SELECT Id FROM dbo.Country WHERE TwoLetterIsoCode = 'FR'").fetchval()
    role_inscrit = cur.execute("SELECT Id FROM dbo.CustomerRole WHERE SystemName = 'Registered'").fetchval()

    # Catalogue : produits vendables, coût d'achat renseigné s'il est absent
    cur.execute("""UPDATE dbo.Product SET ProductCost = ROUND(Price * (0.55 + (ABS(CHECKSUM(Id)) % 20) / 100.0), 2)
                   WHERE Price > 0 AND ProductCost = 0""")
    produits = cur.execute("""SELECT Id, Price, ProductCost FROM dbo.Product
                              WHERE Price > 0 AND Deleted = 0 AND Published = 1 AND IsGiftCard = 0 ORDER BY Id""").fetchall()
    # Popularité : quelques best-sellers, une longue traîne, prix bas plus vendus
    popularite = [random.paretovariate(1.6) / (1 + float(p.Price) / 800) for p in produits]

    # 1) Clients et adresses
    clients = []
    for i in range(args.clients):
        prenom, nom = random.choice(PRENOMS), random.choice(NOMS)
        email = f"{prenom.lower()}.{nom.lower()}.{i + 1:04d}@{DOMAINE}"
        g = random.choices(geo, weights=poids_geo)[0]
        cp = code_postal(g.code_departement)
        # Croissance : plus d'inscriptions récentes
        cree = DEBUT + (FIN - DEBUT) * (random.random() ** 0.7)
        cur.execute("""INSERT INTO dbo.Address (CountryId, StateProvinceId, FirstName, LastName, Email, Company,
                           County, City, Address1, Address2, ZipPostalCode, PhoneNumber, FaxNumber, CustomAttributes, CreatedOnUtc)
                       OUTPUT INSERTED.Id VALUES (?, NULL, ?, ?, ?, NULL, NULL, ?, ?, NULL, ?, ?, NULL, NULL, ?)""",
                    france, prenom, nom, email, g.chef_lieu_departement,
                    f"{random.randint(1, 120)} rue {random.choice(NOMS)}", cp,
                    f"0{random.randint(6, 7)}{random.randint(10000000, 99999999)}", cree)
        adresse = cur.fetchval()
        cur.execute("""INSERT INTO dbo.Customer (Username, Email, FirstName, LastName, Gender, ZipPostalCode, City,
                           StreetAddress, Phone, CustomerGuid, CountryId, BillingAddress_Id, ShippingAddress_Id,
                           VatNumberStatusId, IsTaxExempt, AffiliateId, VendorId, HasShoppingCartItems, RequireReLogin,
                           FailedLoginAttempts, Active, Deleted, IsSystemAccount, CreatedOnUtc, LastActivityDateUtc,
                           RegisteredInStoreId, MustChangePassword, StateProvinceId)
                       OUTPUT INSERTED.Id VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, ?, ?, 1, 0, 0)""",
                    email, email, prenom, nom, random.choice(["M", "F"]), cp, g.chef_lieu_departement,
                    f"{random.randint(1, 120)} rue {random.choice(NOMS)}", str(uuid.uuid4()), france,
                    adresse, adresse, cree, cree)
        client = cur.fetchval()
        cur.execute("INSERT INTO dbo.CustomerAddresses (Customer_Id, Address_Id) VALUES (?, ?)", client, adresse)
        cur.execute("INSERT INTO dbo.Customer_CustomerRole_Mapping (Customer_Id, CustomerRole_Id) VALUES (?, ?)",
                    client, role_inscrit)
        # Fidélité : nombre de commandes très variable
        nb = min(int(random.expovariate(1 / 6.5)) + 1, 40)
        clients.append((client, adresse, cree, nb))
    cn.commit()
    print(f"{len(clients)} clients créés.")

    # 2) Commandes et lignes
    maintenant = FIN
    nb_commandes = nb_lignes = 0
    for client, adresse, cree, nb in clients:
        for _ in range(nb):
            date = date_aleatoire(cree, FIN)
            age = (maintenant - date).days
            lignes = []
            for p in random.choices(produits, weights=popularite, k=random.choices([1, 2, 3, 4], [55, 28, 12, 5])[0]):
                if p.Id not in [l[0].Id for l in lignes]:
                    lignes.append((p, random.choices([1, 2, 3], [80, 15, 5])[0]))
            sous_total = sum(float(p.Price) * q for p, q in lignes)
            transport = tirage(TRANSPORTS)
            frais = 0.0 if transport == "Pickup in store" or sous_total > 500 else (14.9 if transport == "Next Day Air" else 5.9)
            annulee = random.random() < 0.04
            if annulee:
                statut, expedition, paiement = 40, 20, 50
            elif age > 7:
                statut, expedition, paiement = 30, 40, 30
            elif age > 2:
                statut, expedition, paiement = 20, 30, 30
            else:
                statut, expedition, paiement = random.choice([(10, 20, 10), (20, 20, 30)])
            paye = date + timedelta(minutes=random.randint(1, 30)) if paiement == 30 else None
            tva = round(sous_total * 0.2, 2)
            frais_ttc = round(frais * 1.2, 2)
            guid = str(uuid.uuid4())
            cur.execute("""INSERT INTO dbo.[Order] (CustomOrderNumber, BillingAddressId, CustomerId, ShippingAddressId,
                               CustomerIp, OrderGuid, StoreId, PickupInStore, OrderStatusId, ShippingStatusId, PaymentStatusId,
                               PaymentMethodSystemName, CustomerCurrencyCode, CurrencyRate, CustomerTaxDisplayTypeId,
                               OrderSubtotalInclTax, OrderSubtotalExclTax, OrderSubTotalDiscountInclTax, OrderSubTotalDiscountExclTax,
                               OrderShippingInclTax, OrderShippingExclTax, PaymentMethodAdditionalFeeInclTax, PaymentMethodAdditionalFeeExclTax,
                               TaxRates, OrderTax, OrderDiscount, OrderTotal, RefundedAmount, CustomerLanguageId, AffiliateId,
                               AllowStoringCreditCardNumber, PaidDateUtc, ShippingMethod, Deleted, CreatedOnUtc)
                           OUTPUT INSERTED.Id
                           VALUES ('', ?, ?, ?, NULL, ?, 1, ?, ?, ?, ?, ?, 'EUR', 1, 1, ?, ?, 0, 0, ?, ?, 0, 0,
                                   '20:' + CAST(? AS varchar(20)), ?, 0, ?, ?, 1, 0, 0, ?, ?, 0, ?)""",
                        adresse, client, adresse, guid, 1 if transport == "Pickup in store" else 0,
                        statut, expedition, paiement, tirage(PAIEMENTS),
                        round(sous_total * 1.2, 2), round(sous_total, 2), frais_ttc, frais, tva, tva + round(frais * 0.2, 2),
                        round(sous_total * 1.2 + frais_ttc, 2), round(sous_total * 1.2 + frais_ttc, 2) if paiement == 40 else 0,
                        paye, transport, date)
            commande = cur.fetchval()
            cur.execute("UPDATE dbo.[Order] SET CustomOrderNumber = CAST(Id AS varchar(20)) WHERE Id = ?", commande)
            cur.executemany("""INSERT INTO dbo.OrderItem (OrderId, ProductId, OrderItemGuid, Quantity, UnitPriceInclTax,
                                   UnitPriceExclTax, PriceInclTax, PriceExclTax, DiscountAmountInclTax, DiscountAmountExclTax,
                                   OriginalProductCost, DownloadCount, IsDownloadActivated)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 0, 0)""",
                            [(commande, p.Id, str(uuid.uuid4()), q, round(float(p.Price) * 1.2, 2), float(p.Price),
                              round(float(p.Price) * 1.2 * q, 2), round(float(p.Price) * q, 2), float(p.ProductCost))
                             for p, q in lignes])
            nb_commandes += 1
            nb_lignes += len(lignes)
        cn.commit()
    print(f"{nb_commandes} commandes et {nb_lignes} lignes créées.")


if __name__ == "__main__":
    main()
