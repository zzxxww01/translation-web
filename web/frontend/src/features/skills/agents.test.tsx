// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CHAT_AGENT, findAgent, normalizeCatalog } from './agents';
import { NewRunForm } from './components/NewRunForm';
import type { Agent } from './types';

const startRun = vi.hoisted(() => vi.fn());
vi.mock('./api', () => ({ startRun }));
vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

const SERVER: Partial<Agent>[] = [
  { name: '', title: 'Claude', icon: 'chat', description: '什么都能聊', hint: '想问什么都可以', examples: ['查一下 HBM4'], available: true },
  { name: 'video-bilingual-subber', title: '视频字幕', icon: 'video', description: '加字幕', hint: '贴视频链接', examples: ['这个视频加中英双语字幕：'], available: true },
  { name: 'podcast-cn-dubber', title: '播客配音', icon: 'podcast', description: '', hint: '', examples: [], available: false },
];

describe('normalizeCatalog', () => {
  it('keeps chat first and fills fields an older server does not send', () => {
    const catalog = normalizeCatalog([{ name: 'x', description: 'X 的简介', available: true }]);
    expect(catalog[0]).toEqual(CHAT_AGENT);
    expect(catalog[1]).toMatchObject({ name: 'x', title: 'x', icon: 'skill', hint: '', examples: [] });
    expect(normalizeCatalog(SERVER).map(a => a.name)).toEqual(['', 'video-bilingual-subber', 'podcast-cn-dubber']);
  });

  it('finds the agent of a run, falling back for skills no longer listed', () => {
    const catalog = normalizeCatalog(SERVER);
    expect(findAgent(catalog, '').title).toBe('Claude');
    expect(findAgent(catalog, 'video-bilingual-subber').title).toBe('视频字幕');
    expect(findAgent(catalog, 'gone')).toMatchObject({ title: 'gone', icon: 'skill' });
  });
});

describe('NewRunForm', () => {
  let root: Root;
  let host: HTMLDivElement;

  const button = (label: string) =>
    Array.from(host.querySelectorAll('button')).find(el => el.textContent?.trim() === label || el.getAttribute('aria-label') === label);
  const textarea = () => host.querySelector('textarea')!;
  const click = async (label: string) => {
    expect(button(label), `button「${label}」`).toBeDefined();
    await act(async () => {
      button(label)!.click();
      await new Promise(resolve => setTimeout(resolve, 20));
    });
  };

  beforeEach(async () => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
    startRun.mockReset().mockResolvedValue({ id: 'r1' });
    host = document.createElement('div');
    document.body.appendChild(host);
    root = createRoot(host);
    await act(async () => {
      root.render(
        <QueryClientProvider client={new QueryClient()}>
          <NewRunForm catalog={normalizeCatalog(SERVER)} maxUploadMb={95} onStarted={() => {}} />
        </QueryClientProvider>
      );
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  it('chats with Claude until an agent is picked, then hints what that agent needs', async () => {
    expect(textarea().placeholder).toBe('想问什么都可以');
    expect(button('播客配音')!.disabled).toBe(true); // 服务器上没装

    await click('视频字幕');
    expect(button('视频字幕')!.getAttribute('aria-pressed')).toBe('true');
    expect(textarea().placeholder).toBe('贴视频链接');
    expect(host.textContent).toContain('加字幕');

    await click('不用视频字幕，改为和 Claude 聊');
    expect(textarea().placeholder).toBe('想问什么都可以');
  });

  it('starts the task on Codex once Codex is picked, and remembers the choice', async () => {
    await click('Codex');
    expect(button('Codex')!.getAttribute('aria-checked')).toBe('true');
    expect(localStorage.getItem('momo.agent.harness')).toBe('codex');
    await click('视频字幕');
    await click('这个视频加中英双语字幕：');
    await click('开始');
    expect(startRun).toHaveBeenCalledWith(expect.objectContaining({ skill: 'video-bilingual-subber', harness: 'codex' }), expect.any(Function));
    localStorage.removeItem('momo.agent.harness');
  });

  it('fills an example and starts the task with the picked agent', async () => {
    await click('视频字幕');
    await click('这个视频加中英双语字幕：');
    expect(textarea().value).toBe('这个视频加中英双语字幕：');

    await click('开始');
    expect(startRun).toHaveBeenCalledWith(
      { skill: 'video-bilingual-subber', message: '这个视频加中英双语字幕：', files: [], harness: 'claude' },
      expect.any(Function)
    );
  });
});
