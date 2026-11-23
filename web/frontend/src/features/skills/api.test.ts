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

it('dismisses the awaiting prompt without retrying', async () => {
  const fetch = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ id: 'r1' })));
  vi.stubGlobal('fetch', fetch);
  await skillsApi.dismissAwaiting('r1');
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toMatch(/\/skills\/runs\/r1\/dismiss-awaiting$/);
  expect(fetch.mock.calls[0][1].method).toBe('POST');
});
