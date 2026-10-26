import fabric.functions as fn

udf = fn.UserDataFunctions()

@udf.connection(argName="wh", alias="AmazingZoneWH")
@udf.function()
def enregistrer_objectif(wh: fn.FabricSqlConnection, mois: str, univers: str,
                         montant: float, auteur: str) -> str:
    if montant < 0:
        raise fn.UserThrownError("Un objectif ne peut pas être négatif.")
    connexion = wh.connect()
    curseur = connexion.cursor()
    # un seul objectif par mois et par univers : une nouvelle saisie remplace la précédente
    curseur.execute("DELETE FROM saisie.objectif_vente WHERE Mois = ? AND Univers = ?",
                    mois, univers)
    curseur.execute("INSERT INTO saisie.objectif_vente (Mois, Univers, ObjectifHT, SaisiPar, SaisiLe) "
                    "VALUES (?, ?, ?, ?, SYSUTCDATETIME())",
                    mois, univers, montant, auteur)
    connexion.commit()
    curseur.close()
    connexion.close()
    return (f"Objectif de {montant:,.0f} € HT enregistré pour {univers}, {mois}. "
            "Il apparaîtra dans le rapport après la prochaine actualisation du modèle.")
