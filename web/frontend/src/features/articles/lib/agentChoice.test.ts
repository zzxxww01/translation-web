// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest';
import { loadModel } from '@/features/skills/models';
import { loadHarness } from '@/features/skills/harness';
import { ARTICLE_HARNESSES, loadAgentChoice, rememberedModel, saveAgentChoice } from './agentChoice';

describe('agentChoice', () => {
  beforeEach(() => localStorage.clear());

  it('lists Codex first and defaults to it', () => {
    expect(ARTICLE_HARNESSES.map(item => item.id)).toEqual(['codex', 'claude', 'antigravity']);
    expect(loadAgentChoice()).toEqual({ harness: 'codex', model: '' });
  });

  it('remembers the model per agent in the same place as the Agent page', () => {
    saveAgentChoice({ harness: 'claude', model: ' opus ' });
    saveAgentChoice({ harness: 'codex', model: 'gpt-5.5-codex' });
    expect(loadHarness('four-step-translate', 'claude')).toBe('codex');
    expect(loadModel('four-step-translate', 'claude')).toBe('opus');
    expect(rememberedModel('codex')).toBe('gpt-5.5-codex');
    expect(loadAgentChoice()).toEqual({ harness: 'codex', model: 'gpt-5.5-codex' });
    expect(loadAgentChoice('claude')).toEqual({ harness: 'claude', model: 'opus' });
  });

  it('only picks from the allowed agents', () => {
    saveAgentChoice({ harness: 'codex', model: '' });
    expect(loadAgentChoice(undefined, ['claude', 'antigravity']).harness).toBe('claude');
    expect(loadAgentChoice('codex', ['antigravity']).harness).toBe('antigravity');
  });
});
