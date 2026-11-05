import { entity, boolean, date, int, text, role } from '@microsoft/rayfin-core';
import { Source } from '@microsoft/rayfin-connectors';

// Écrit à la main : la découverte du connecteur ne liste que les tables, pas la vue api.sante_entrepots
// (sql/sante_entrepots.sql). Entité sans clé, en lecture seule.
@role('authenticated', ['read'])
@entity()
export class SanteEntrepots extends Source({ schema: 'api', table: 'sante_entrepots', primaryKey: [] }) {
  @text({ optional: true, column: 'CodeEntrepot' }) codeEntrepot?: string;
  @date({ optional: true, column: 'DernierEvenement' }) dernierEvenement?: Date;
  @date({ optional: true, column: 'DerniereCopie' }) derniereCopie?: Date;
  @int({ optional: true, column: 'MinutesSansEvenement' }) minutesSansEvenement?: number;
  @boolean({ optional: true, column: 'EntrepotMuet' }) entrepotMuet?: boolean;
  @int({ optional: true, column: 'EvenementsDerniereHeure' }) evenementsDerniereHeure?: number;
  @int({ optional: true, column: 'ExpeditionsDerniereHeure' }) expeditionsDerniereHeure?: number;
}
