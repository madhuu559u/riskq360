import apiClient from './client';
import type {
  SystemConfig,
  FeatureFlags,
  PromptTemplates,
  HedisMeasureCatalogResponse,
} from '../types/api';

export async function getConfig(): Promise<SystemConfig> {
  const { data } = await apiClient.get<SystemConfig>('/config');
  return data;
}

export async function updateConfig(config: Partial<SystemConfig>): Promise<SystemConfig> {
  const { data } = await apiClient.put<SystemConfig>('/config', config as Record<string, unknown>);
  return data;
}

export async function getPrompts(): Promise<PromptTemplates> {
  const { data } = await apiClient.get<PromptTemplates>('/config/prompts');
  return data;
}

export async function updatePrompt(
  name: string,
  promptData: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.put<Record<string, unknown>>(
    `/config/prompts/${name}`,
    promptData,
  );
  return data;
}

export async function getFeatureFlags(): Promise<FeatureFlags> {
  const { data } = await apiClient.get<FeatureFlags>('/config/feature-flags');
  return data;
}

export async function updateFeatureFlags(flags: FeatureFlags): Promise<FeatureFlags> {
  const { data } = await apiClient.put<FeatureFlags>('/config/feature-flags', flags);
  return data;
}

export async function getModelVersions(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>('/config/model-versions');
  return data;
}

export async function getHedisMeasureCatalog(): Promise<HedisMeasureCatalogResponse> {
  const { data } = await apiClient.get<HedisMeasureCatalogResponse>('/config/hedis/measures');
  return data;
}

export async function updateHedisMeasureProfile(
  activeMeasureIds: string[],
  profileId = 'custom',
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.put<Record<string, unknown>>('/config/hedis/profile', {
    active_measure_ids: activeMeasureIds,
    profile_id: profileId,
    updated_by: 'ui',
  });
  return data;
}

export async function getHedisMeasureDefinition(measureId: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>(`/config/hedis/measures/${measureId}`);
  return data;
}

export async function saveHedisMeasureDefinition(
  measureId: string,
  definition: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.put<Record<string, unknown>>(`/config/hedis/measures/${measureId}`, {
    definition,
    updated_by: 'ui',
  });
  return data;
}

export async function deleteHedisMeasureDefinition(measureId: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.delete<Record<string, unknown>>(`/config/hedis/measures/${measureId}`);
  return data;
}
