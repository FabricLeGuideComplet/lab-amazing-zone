import type { GraphQLBackedConnector } from '@microsoft/rayfin-connector-fabric-graphql';
import type { ConnectorConfig } from '@microsoft/rayfin-connectors';

import { SanteEntrepots } from './SanteEntrepots.js';

export { SanteEntrepots } from './SanteEntrepots.js';

// Point de terminaison SQL du Lakehouse AmazingZoneLK, en lecture seule
export const connectorConfig = {
  connector: 'fabric-sqlanalytics',
  operations: ['read'],
  entities: { SanteEntrepots },
} as const satisfies ConnectorConfig;

export type EvenementswmsSchema = GraphQLBackedConnector<{ SanteEntrepots: typeof SanteEntrepots }, typeof connectorConfig>;
