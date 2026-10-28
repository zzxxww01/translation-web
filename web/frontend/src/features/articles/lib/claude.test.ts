// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorWrapper } from '@/shared/api/client';
import type { RunMeta } from '@/features/skills/types';

const importClaude = vi.hoisted(() => vi.fn());
vi.mock('../api', () => ({ articlesApi: { importClaude } }));
vi.mock('@/features/skills/api', async importOriginal => ({
  ...(await importOriginal<object>()),
  skillsApi: { files: vi.fn().mockResolvedValue([
    { path: 'out/zh.md', size: 1, mtime: 1 }, { path: 'out/en.md', size: 1, mtime: 1 },
  ]) },
}));

import { AlignmentTooLow, importClaudeTrack } from './claude';

const run = { id: 'r1', harness: 'codex' } as RunMeta;

describe('importClaudeTrack 409 handling', () => {
  beforeEach(() => { vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response('text'))); });
  afterEach(() => { vi.unstubAllGlobals(); importClaude.mockReset(); });

  it('maps only ALIGNMENT_LOW 409s to AlignmentTooLow', async () => {
    importClaude.mockRejectedValue(new ApiErrorWrapper('对不上', 409, { detail: '对不上', error_code: 'ALIGNMENT_LOW' }));
    await expect(importClaudeTrack('p1', run)).rejects.toBeInstanceOf(AlignmentTooLow);
  });

  it('rethrows other 409s unchanged', async () => {
    const other = new ApiErrorWrapper('冲突', 409, { detail: '冲突', error_code: 'RESOURCE_CONFLICT' });
    importClaude.mockRejectedValue(other);
    await expect(importClaudeTrack('p1', run)).rejects.toBe(other);
  });
});
