import fabric.functions as fn

udf = fn.UserDataFunctions()

@udf.connection(argName="wh", alias="AmazingZoneWH")
@udf.function()
def stock_disponible(wh: fn.FabricSqlConnection, sku: str) -> dict:
    if not sku or len(sku) > 50:
        raise fn.UserThrownError("Référence produit invalide.")
    connexion = wh.connect()
    curseur = connexion.cursor()
    curseur.execute("SELECT code_entrepot, quantite_disponible, date_maj_wms "
                    "FROM api.stock_disponible WHERE sku = ? ORDER BY code_entrepot", sku)
    entrepots = [{"code_entrepot": e, "quantite_disponible": q,
                  "date_maj_wms": d.isoformat() if d else None}
                 for e, q, d in curseur.fetchall()]
    curseur.close()
    connexion.close()
    total = sum(e["quantite_disponible"] for e in entrepots)
    # règle métier portée par la fonction : le site n'annonce « en stock » qu'au-delà d'un seuil de sécurité
    return {"sku": sku, "total_disponible": total, "en_stock": total >= 5, "entrepots": entrepots}
