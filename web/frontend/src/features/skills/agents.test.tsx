// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CHAT_AGENT, findAgent, normalizeCatalog } from './agents';
import { NewRunForm } from './components/NewRunForm';
import type { Agent } from './types';

const { startRun, models } = vi.hoisted(() => ({ startRun: vi.fn(), models: vi.fn() }));
vi.mock('./api', () => ({ startRun, AUTO_REPLY_MINUTES: 10, skillsApi: { models } }));
vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

const SERVER: Partial<Agent>[] = [
  { name: '', title: '通用 Agent', icon: 'general', description: '什么都能问', hint: '想问什么都可以', examples: ['查一下 HBM4'], harness: 'claude', available: true },
  { name: 'four-step-translate', title: '翻译 Agent', icon: 'translate', description: '精翻英文长文', hint: '传文章 HTML', examples: [], harness: 'codex', available: true },
  { name: 'video-bilingual-subber', title: '字幕 Agent', icon: 'subtitle', description: '加字幕', hint: '贴视频链接', examples: ['这个视频加中英双语字幕：'], harness: 'claude', available: true },
  { name: 'podcast-cn-dubber', title: '播客 Agent', icon: 'podcast', description: '', hint: '', examples: [], available: false },
];

describe('normalizeCatalog', () => {
  it('keeps the general agent first and fills fields an older server does not send', () => {
    const catalog = normalizeCatalog([{ name: 'x', description: 'X 的简介', available: true }]);
    expect(catalog[0]).toEqual(CHAT_AGENT);
    expect(catalog[1]).toMatchObject({ name: 'x', title: 'x', icon: 'skill', hint: '', examples: [], harness: 'claude' });
    expect(normalizeCatalog(SERVER).map(a => a.name)).toEqual(['', 'four-step-translate', 'video-bilingual-subber', 'podcast-cn-dubber']);
  });

  it('finds the agent of a conversation, falling back for skills no longer listed', () => {
    const catalog = normalizeCatalog(SERVER);
    expect(findAgent(catalog, '').title).toBe('通用 Agent');
    expect(findAgent(catalog, 'video-bilingual-subber').title).toBe('字幕 Agent');
    expect(findAgent(catalog, 'gone')).toMatchObject({ title: 'gone', icon: 'skill' });
  });
});

describe('NewRunForm', () => {
  let root: Root;
  let host: HTMLDivElement;

  const radio = (group: string, name: string) =>
    Array.from(host.querySelectorAll(`[role="radiogroup"][aria-label="${group}"] [role="radio"]`)).find(el =>
      el.textContent?.startsWith(name)
    ) as HTMLButtonElement | undefined;
  const button = (label: string) => Array.from(host.querySelectorAll('button')).find(el => el.textContent?.trim() === label);
  const textarea = () => host.querySelector('textarea')!;
  const click = async (el: HTMLElement | undefined, what: string) => {
    expect(el, what).toBeDefined();
    await act(async () => {
      el!.click();
      await new Promise(resolve => setTimeout(resolve, 20));
    });
  };

  beforeEach(async () => {
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
    localStorage.clear();
    startRun.mockReset().mockResolvedValue({ id: 'r1' });
    models.mockReset().mockImplementation(async (harness: string) => ({
      models: harness === 'codex'
        ? [{ id: 'gpt-6-astra', label: 'GPT-6 Astra', description: '' }]
        : [{ id: 'opus', label: 'Claude Opus', description: '' }],
      default_model: null, source: 'runtime', warning: null,
    }));
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

  it('starts on the general agent; picking a card says what to give that agent', async () => {
    expect(radio('选 Agent', '通用 Agent')!.getAttribute('aria-checked')).toBe('true');
    expect(textarea().placeholder).toBe('想问什么都可以');
    expect(radio('选 Agent', '播客 Agent')!.disabled).toBe(true); // 服务器上没装
    expect(host.textContent).toContain('服务器上还没装这个 Agent');

    await click(radio('选 Agent', '字幕 Agent'), '字幕卡片');
    expect(radio('选 Agent', '字幕 Agent')!.getAttribute('aria-checked')).toBe('true');
    expect(textarea().placeholder).toBe('贴视频链接');
    expect(host.textContent).toContain('交给 字幕 Agent');
  });

  it('uses each agent\'s default model and remembers a change per agent', async () => {
    expect(radio('模型', 'Claude')!.getAttribute('aria-checked')).toBe('true');
    await click(radio('选 Agent', '翻译 Agent'), '翻译卡片');
    expect(radio('模型', 'Codex')!.getAttribute('aria-checked')).toBe('true'); // 翻译默认 Codex

    await click(radio('模型', 'Claude'), 'Claude');
    expect(JSON.parse(localStorage.getItem('momo.agent.model')!)).toEqual({ 'four-step-translate': 'claude' });
    await click(radio('选 Agent', '通用 Agent'), '通用卡片');
    await click(radio('选 Agent', '翻译 Agent'), '翻译卡片');
    expect(radio('模型', 'Claude')!.getAttribute('aria-checked')).toBe('true');
  });

  it('fills an example and starts the conversation with the picked agent', async () => {
    await click(radio('选 Agent', '字幕 Agent'), '字幕卡片');
    await click(button('这个视频加中英双语字幕：'), '示例');
    expect(textarea().value).toBe('这个视频加中英双语字幕：');

    await click(button('开始'), '开始');
    expect(startRun).toHaveBeenCalledWith(
      { skill: 'video-bilingual-subber', message: '这个视频加中英双语字幕：', files: [], harness: 'claude', autoReplyMinutes: 10 },
      expect.any(Function)
    );
  });

  it('can turn off auto-continue', async () => {
    await click(button('查一下 HBM4'), '示例');
    await click(host.querySelector('input[type="checkbox"]') as HTMLInputElement, '自动继续');
    await click(button('开始'), '开始');
    expect(startRun).toHaveBeenCalledWith(expect.objectContaining({ skill: '', autoReplyMinutes: 0 }), expect.any(Function));
  });

  it('submits the concrete model and remembers it separately for each provider', async () => {
    await click(radio('模型', 'Codex'), 'Codex');
    const picker = host.querySelector('select[aria-label="具体模型"]') as HTMLSelectElement;
    expect(picker).not.toBeNull();
    await act(async () => {
      picker.value = 'gpt-6-astra';
      picker.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await click(radio('模型', 'Claude'), 'Claude');
    expect((host.querySelector('select[aria-label="具体模型"]') as HTMLSelectElement).value).toBe('');
    await click(radio('模型', 'Codex'), 'Codex');
    expect((host.querySelector('select[aria-label="具体模型"]') as HTMLSelectElement).value).toBe('gpt-6-astra');
    await click(button('查一下 HBM4'), '示例');
    await click(button('开始'), '开始');
    expect(startRun).toHaveBeenCalledWith(expect.objectContaining({ harness: 'codex', model: 'gpt-6-astra' }), expect.any(Function));
  });

  it('allows a custom model ID without passing it to another agent', async () => {
    await click(radio('模型', 'Codex'), 'Codex');
    const picker = host.querySelector('select[aria-label="具体模型"]') as HTMLSelectElement;
    expect(picker).not.toBeNull();
    await act(async () => {
      picker.value = '__custom__';
      picker.dispatchEvent(new Event('change', { bubbles: true }));
    });
    const input = host.querySelector('input[aria-label="模型 ID"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, 'gpt-future');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await click(radio('选 Agent', '翻译 Agent'), '翻译卡片');
    expect((host.querySelector('select[aria-label="具体模型"]') as HTMLSelectElement).value).toBe('');
    await click(radio('选 Agent', '通用 Agent'), '通用卡片');
    expect((host.querySelector('input[aria-label="模型 ID"]') as HTMLInputElement).value).toBe('gpt-future');
  });
});
