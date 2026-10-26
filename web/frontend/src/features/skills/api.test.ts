import { afterEach, expect, it, vi } from 'vitest';
import { skillsApi } from './api';

afterEach(() => vi.unstubAllGlobals());

it('sends an explicit refresh flag only when requested', async () => {
  const fetch = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ models: [] })));
  vi.stubGlobal('fetch', fetch);
  await skillsApi.models('antigravity');
  expect(fetch.mock.calls[0][0]).toMatch(/\/skills\/models\/antigravity$/);
  await skillsApi.models('antigravity', true);
  expect(fetch.mock.calls[1][0]).toMatch(/\/skills\/models\/antigravity\?refresh=true$/);
});
