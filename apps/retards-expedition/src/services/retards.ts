import { getRayfinClient } from './rayfinClient';

/** Commande expédiée au-delà de 24 heures, lue dans le modèle sémantique « Ventes et logistique ». */
export interface Retard {
  numeroCommande: string;
  codeEntrepot: string;
  transporteur: string;
  dateExpedition: string;
  delaiHeures: number;
}

export type Cause = 'rupture' | 'meteo' | 'transporteur' | 'preparation' | 'pic' | 'autre';

export const LIBELLES_CAUSES: Record<Cause, string> = {
  rupture: 'Rupture de stock',
  meteo: 'Intempéries',
  transporteur: 'Transporteur',
  preparation: 'Erreur de préparation',
  pic: "Pic d'activité",
  autre: 'Autre',
};

export interface CauseSaisie {
  id: string;
  numeroCommande: string;
  cause: Cause;
  commentaire?: string;
  saisiPar: string;
  saisiLe: Date;
}

// Retards des quatorze derniers jours expédiés : la requête ne contient aucune valeur saisie par l'utilisateur.
const DAX_RETARDS = "DEFINE\n    VAR Expediees = FILTER ( 'Expéditions', NOT ISBLANK ( 'Expéditions'[DateExpeditionId] ) )\n    VAR DernierJour = MAXX ( Expediees, RELATED ( Calendrier[Date] ) )\nEVALUATE\nSELECTCOLUMNS (\n    FILTER (\n        Expediees,\n        'Expéditions'[EstExpedieeSous24h] = FALSE ()\n            && RELATED ( Calendrier[Date] ) > DernierJour - 14\n    ),\n    \"NumeroCommande\", 'Expéditions'[NumeroCommande],\n    \"CodeEntrepot\", RELATED ( 'Entrepôt'[Code entrepôt] ),\n    \"Transporteur\", RELATED ( Transporteur[Transporteur] ),\n    \"DateExpedition\", RELATED ( Calendrier[Date] ),\n    \"DelaiHeures\", 'Expéditions'[DelaiPreparationHeures]\n)\nORDER BY [DateExpedition] DESC, [NumeroCommande]";

export async function getRetards(): Promise<Retard[]> {
  const result = await getRayfinClient().connectors.venteslogistique.executeQuery({ query: DAX_RETARDS });
  if (result.status !== 'success') throw new Error(result.error.message);
  return result.table.rows.map((r) => ({
    numeroCommande: String(r[0]),
    codeEntrepot: String(r[1]),
    transporteur: String(r[2] ?? ''),
    dateExpedition: String(r[3]).slice(0, 10),
    delaiHeures: Number(r[4]),
  }));
}

export async function getCauses(): Promise<CauseSaisie[]> {
  const rows = await getRayfinClient()
    .data.CauseRetard.select(['id', 'numeroCommande', 'cause', 'commentaire', 'saisiPar', 'saisiLe'])
    .first(1000)
    .execute();
  return rows as CauseSaisie[];
}

export async function enregistrerCause(
  retard: Retard,
  cause: Cause,
  commentaire: string,
  existante?: CauseSaisie
): Promise<void> {
  const client = getRayfinClient();
  const session = client.auth.getSession();
  if (!session.isAuthenticated || !session.user) throw new Error("Session expirée : reconnectez-vous.");
  const auteur = session.user.email ?? session.user.id;
  const valeurs = { cause, commentaire: commentaire || undefined, saisiPar: auteur, saisiLe: new Date() };
  if (existante) {
    await client.data.CauseRetard.update({ id: existante.id }, valeurs);
  } else {
    await client.data.CauseRetard.create({
      numeroCommande: retard.numeroCommande,
      codeEntrepot: retard.codeEntrepot,
      ...valeurs,
    });
  }
}
