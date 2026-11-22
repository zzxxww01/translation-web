// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { chatApi, type ChatMessage, type ChatSession } from './api';
import { useChatStore } from './chatStore';
import { ChatFeature } from './index';

vi.mock('@/components/ModelSelector', () => ({ ModelSelector: () => null }));
vi.mock('@/components/layout/HeaderSlot', () => ({ PageActions: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));

let host: HTMLDivElement;
let root: Root;

const doc = (id: string, messages: Partial<ChatMessage>[] = [], title = '新对话'): ChatSession => ({
  id, title, created_at: 1, updated_at: 1,
  messages: messages.map((m, i) => ({ id: `m${i}`, role: 'user', content: '', ...m })),
});

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  Element.prototype.scrollTo = vi.fn();
  useChatStore.setState({ currentId: null, messages: [], draft: '', model: 'gpt-6.2-sol', webSearch: true });
  vi.spyOn(chatApi, 'list').mockResolvedValue({ sessions: [] });
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
});

afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const type = async (text: string) => {
  const input = host.querySelector('textarea[aria-label="输入消息"]') as HTMLTextAreaElement;
  await act(async () => useChatStore.getState().setDraft(text));
  await act(async () => { input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); });
};
const button = (label: string) => Array.from(host.querySelectorAll('button')).find(b => b.textContent?.includes(label))!;

it('creates a session on the first message, sends with model and web search, and shows sources', async () => {
  vi.spyOn(chatApi, 'create').mockResolvedValue(doc('c_1'));
  const send = vi.spyOn(chatApi, 'send').mockResolvedValue(doc('c_1', [
    { role: 'user', content: '今天有什么新闻' },
    { role: 'assistant', content: '**英伟达**…', sources: [{ title: 'FT', url: 'https://ft.com/a' }] },
  ]));
  await act(async () => root.render(<ChatFeature />));
  await type('今天有什么新闻');
  expect(send).toHaveBeenCalledWith('c_1', '今天有什么新闻', { model: 'gpt-6.2-sol', web_search: true });
  expect(useChatStore.getState().currentId).toBe('c_1');
  expect(host.querySelector('.skill-md strong')?.textContent).toBe('英伟达');
  expect(host.querySelector('a[href="https://ft.com/a"]')?.textContent).toContain('FT');

  // 关掉联网后再发
  await act(async () => button('联网').click());
  await type('再说说');
  expect(send).toHaveBeenLastCalledWith('c_1', '再说说', { model: 'gpt-6.2-sol', web_search: false });
});

it('keeps the question and retries through the reply endpoint when the answer fails', async () => {
  useChatStore.setState({ currentId: 'c_2' });
  vi.spyOn(chatApi, 'get')
    .mockResolvedValueOnce(doc('c_2'))
    .mockResolvedValueOnce(doc('c_2', [{ role: 'user', content: '你好' }]));
  vi.spyOn(chatApi, 'send').mockRejectedValueOnce(new Error('超时'));
  const reply = vi.spyOn(chatApi, 'reply').mockResolvedValue(doc('c_2', [
    { role: 'user', content: '你好' }, { role: 'assistant', content: '好了', note: '这个模型不能联网，回答没有用搜索' }]));
  await act(async () => root.render(<ChatFeature />));
  await type('你好');
  expect(host.textContent).toContain('没拿到回复：超时');
  expect(host.textContent).toContain('你好');
  await act(async () => button('重试').click());
  expect(reply).toHaveBeenCalledWith('c_2', { model: 'gpt-6.2-sol', web_search: true });
  expect(host.textContent).toContain('好了');
  expect(host.textContent).toContain('这个模型不能联网');
});

it('imports the conversation the old version kept in the browser and lists sessions', async () => {
  useChatStore.setState({ messages: [{ role: 'user', content: '旧问题' }, { role: 'assistant', content: '旧回答' }] });
  const create = vi.spyOn(chatApi, 'create').mockResolvedValue(doc('c_old', [{ role: 'user', content: '旧问题' }], '旧问题'));
  vi.spyOn(chatApi, 'get').mockResolvedValue(doc('c_old', [{ role: 'user', content: '旧问题' }, { role: 'assistant', content: '旧回答' }], '旧问题'));
  vi.mocked(chatApi.list).mockResolvedValue({ sessions: [{ id: 'c_old', title: '旧问题', count: 2, updated_at: 1 }] });
  await act(async () => root.render(<ChatFeature />));
  expect(create).toHaveBeenCalledWith([{ role: 'user', content: '旧问题' }, { role: 'assistant', content: '旧回答' }]);
  expect(useChatStore.getState().messages).toEqual([]);
  expect(useChatStore.getState().currentId).toBe('c_old');
  expect(host.querySelector('aside[aria-label="对话列表"]')?.textContent).toContain('旧问题');
  expect(host.textContent).toContain('旧回答');

  // 新对话：回到空白页，列表里的会话还在
  await act(async () => button('新对话').click());
  expect(useChatStore.getState().currentId).toBeNull();
  expect(host.textContent).toContain('有什么想问的');
});
