import { entity, authenticated, uuid, text, set, date } from '@microsoft/rayfin-core';

/**
 * Cause d'un retard d'expédition, saisie par le chef d'entrepôt pour une commande
 * expédiée au-delà de 24 heures. Une cause par commande ; la suppression n'est pas permise.
 */
@entity()
@authenticated(['read', 'create', 'update'])
export class CauseRetard {
  @uuid() id!: string;
  @text({ min: 1, max: 20 }) numeroCommande!: string;
  @text({ min: 1, max: 10 }) codeEntrepot!: string;
  @set('rupture', 'meteo', 'transporteur', 'preparation', 'pic', 'autre')
  cause!: 'rupture' | 'meteo' | 'transporteur' | 'preparation' | 'pic' | 'autre';
  @text({ max: 500, optional: true }) commentaire?: string;
  @text({ min: 1, max: 256 }) saisiPar!: string;
  @date() saisiLe!: Date;
}
