import {
  ConnectorsRayfinClient,
  resolveRayfinConfig,
  type RayfinRuntimeConfig,
} from '@microsoft/rayfin-client';
import { fabricSemanticModel } from '@microsoft/rayfin-connector-fabric-semanticmodel';

import type { RetardsAppSchema } from '../../rayfin/data/schema';
import {
  type VenteslogistiqueSchema,
  connectorConfig as ventesLogistiqueConfig,
} from '../../rayfin/connectors/venteslogistique/schema';

export interface RayfinClientConfig {
  baseUrl: string;
  publishableKey: string;
  localDev: boolean;
  functionsBaseUrl?: string;
  runtimeConfig?: RayfinRuntimeConfig;
}

type AppConnectorsSchema = { venteslogistique: VenteslogistiqueSchema };
export type AppClient = ConnectorsRayfinClient<RetardsAppSchema, never, AppConnectorsSchema>;

let client: AppClient | null = null;
let localDev = false;

export async function initRayfinClient(config: RayfinClientConfig): Promise<AppClient> {
  if (client) throw new Error('Rayfin client is already initialized.');
  const resolved = await resolveRayfinConfig({
    apiUrl: config.baseUrl,
    publishableKey: config.publishableKey,
    ...config.runtimeConfig,
  });
  client = new ConnectorsRayfinClient<RetardsAppSchema, never, AppConnectorsSchema>(
    {
      baseUrl: resolved.baseUrl!,
      publishableKey: resolved.publishableKey!,
      authStorage: true,
      functionsBaseUrl: config.functionsBaseUrl,
      runtimeConfig: resolved.runtimeConfig,
      connectors: { venteslogistique: ventesLogistiqueConfig },
    },
    { venteslogistique: fabricSemanticModel() }
  );
  localDev = config.localDev;
  return client;
}

export function getRayfinClient(): AppClient {
  if (!client) throw new Error('Rayfin client not initialized. Call bootstrapAuth() first.');
  return client;
}

export function isLocalBackend(): boolean {
  return localDev;
}
