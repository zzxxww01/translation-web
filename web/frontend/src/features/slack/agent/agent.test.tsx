// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import { ResultCards } from './ResultCards';
import { parseResult } from './result';
import { agentSource, SLACK_SKILLS } from './useSlackAgent';

it('binds one agent per thread or DM', () => {
  expect(agentSource('C123', '1794871046.243619')).toBe('slack:C123:1794871046.243619');
  expect(agentSource('D123', null)).toBe('slack:D123');
  expect(SLACK_SKILLS).toEqual({ thread: 'slack-post-translate', dm: 'slack-dm-reply' });
});

it('only accepts known result.json shapes', () => {
  expect(parseResult({ type: 'post_translation', translation: '译文' })?.type).toBe('post_translation');
  expect(parseResult({ type: 'dm_reply', replies: [] })?.type).toBe('dm_reply');
  expect(parseResult({ type: 'other' })).toBeNull();
  expect(parseResult('x')).toBeNull();
  expect(parseResult(null)).toBeNull();
});

it('renders translation and reply cards with copy actions', async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div');
  const root = createRoot(host);
  try {
    await act(async () => root.render(
      <ResultCards
        slackLink={null}
        result={{ type: 'post_translation', summary: '翻译了 X 帖', translation: '中文译文', titles: ['标题一', '标题二'] }}
      />
    ));
    expect(host.textContent).toContain('翻译了 X 帖');
    expect(host.textContent).toContain('中文译文');
    expect(host.textContent).toContain('标题二');
    expect(host.textContent).toContain('3 字');

    await act(async () => root.render(
      <ResultCards
        slackLink="https://team.slack.com/archives/D1"
        result={{
          type: 'dm_reply', pending: true, understanding: '对方要周五前的数据',
          replies: [{ version: 'A', label: '随意', english: 'Sure, by Friday.', chinese: '好的，周五前。' }],
        }}
      />
    ));
    expect(host.textContent).toContain('对方要什么');
    expect(host.textContent).toContain('A · 随意');
    expect(host.textContent).toContain('复制并打开 Slack');
    expect(host.querySelector('a')?.getAttribute('href')).toBe('https://team.slack.com/archives/D1');
  } finally {
    await act(async () => root.unmount());
    vi.unstubAllGlobals();
  }
});
