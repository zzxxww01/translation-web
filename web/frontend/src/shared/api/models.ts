import { apiClient } from './client';
import type { ModelListResponse, LegacyModelListResponse } from '../types';

/**
 * Models API
 */
export const modelsApi = {
  /**
   * Get all available models (grouped by provider)
   */
  getModels: () => apiClient.get<ModelListResponse>('/models'),

  /**
   * Get all available models (legacy flat list)
   */
  getModelsLegacy: () => apiClient.get<LegacyModelListResponse>('/models/legacy'),
};
