import { getRayfinClient } from './rayfinClient';

/** Santé d'un entrepôt, lue dans la vue api.sante_entrepots du Lakehouse (copie OneLake des événements du WMS). */
export interface SanteEntrepot {
  codeEntrepot: string;
  dernierEvenement: Date | null;
  derniereCopie: Date | null;
  minutesSansEvenement: number;
  muet: boolean;
  evenementsDerniereHeure: number;
  expeditionsDerniereHeure: number;
}

export async function getSanteEntrepots(): Promise<SanteEntrepot[]> {
  const lignes = await getRayfinClient().connectors.evenementswms.SanteEntrepots.findMany();
  return lignes
    .map((l) => ({
      codeEntrepot: l.codeEntrepot ?? '?',
      dernierEvenement: l.dernierEvenement ? new Date(l.dernierEvenement) : null,
      derniereCopie: l.derniereCopie ? new Date(l.derniereCopie) : null,
      minutesSansEvenement: l.minutesSansEvenement ?? 0,
      muet: l.entrepotMuet ?? false,
      evenementsDerniereHeure: l.evenementsDerniereHeure ?? 0,
      expeditionsDerniereHeure: l.expeditionsDerniereHeure ?? 0,
    }))
    .sort((a, b) => a.codeEntrepot.localeCompare(b.codeEntrepot));
}
