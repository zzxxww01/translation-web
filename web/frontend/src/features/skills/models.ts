import type { Harness } from './harness';

const STORAGE_KEY = 'momo.agent.concrete-model';

export function loadModel(agent: string, harness: Harness): string {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')[`${agent}:${harness}`];
    return typeof value === 'string' ? value : '';
  } catch {
    return '';
  }
}

export function saveModel(agent: string, harness: Harness, model: string): void {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...saved, [`${agent}:${harness}`]: model }));
  } catch {
    // Local storage is optional; the server still stores the choice on the run.
  }
}
