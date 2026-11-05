import {
  ConnectorsRayfinClient,
  resolveRayfinConfig,
  type RayfinRuntimeConfig,
} from '@microsoft/rayfin-client';

import {
  type EvenementswmsSchema,
  connectorConfig as evenementsWmsConfig,
} from '../../rayfin/connectors/evenementswms/schema';

export interface RayfinClientConfig {
  baseUrl: string;
  publishableKey: string;
  localDev: boolean;
  functionsBaseUrl?: string;
  runtimeConfig?: RayfinRuntimeConfig;
}

// Aucune donnée propre à l'application : seul le connecteur vers le point de terminaison SQL est déclaré
type AppConnectorsSchema = { evenementswms: EvenementswmsSchema };
export type AppClient = ConnectorsRayfinClient<Record<string, never>, never, AppConnectorsSchema>;

let client: AppClient | null = null;
let localDev = false;

export async function initRayfinClient(config: RayfinClientConfig): Promise<AppClient> {
  if (client) throw new Error('Rayfin client is already initialized.');
  const resolved = await resolveRayfinConfig({
    apiUrl: config.baseUrl,
    publishableKey: config.publishableKey,
    ...config.runtimeConfig,
  });
  client = new ConnectorsRayfinClient<Record<string, never>, never, AppConnectorsSchema>(
    {
      baseUrl: resolved.baseUrl!,
      publishableKey: resolved.publishableKey!,
      authStorage: true,
      functionsBaseUrl: config.functionsBaseUrl,
      runtimeConfig: resolved.runtimeConfig,
      connectors: { evenementswms: evenementsWmsConfig },
    }
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
