// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { chatApi } from './api';
import { useChatStore } from './chatStore';
import { ChatFeature } from './index';

vi.mock('@/components/ModelSelector', () => ({ ModelSelector: () => null }));

let host: HTMLDivElement;
let root: Root;

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  Element.prototype.scrollTo = vi.fn();
  useChatStore.setState({ messages: [], draft: '', model: 'gpt-6.2-sol' });
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

it('sends the whole conversation with the chosen model and shows the reply', async () => {
  const send = vi.spyOn(chatApi, 'send')
    .mockResolvedValueOnce({ reply: '**HBM** 带宽更高' })
    .mockResolvedValueOnce({ reply: '贵' });
  await act(async () => root.render(<ChatFeature />));
  await type('HBM 和 GDDR 有什么区别？');
  expect(send).toHaveBeenLastCalledWith({ messages: [{ role: 'user', content: 'HBM 和 GDDR 有什么区别？' }], model: 'gpt-6.2-sol' });
  expect(host.querySelector('.skill-md strong')?.textContent).toBe('HBM');
  await type('缺点呢？');
  expect(send.mock.calls[1][0].messages).toEqual([
    { role: 'user', content: 'HBM 和 GDDR 有什么区别？' },
    { role: 'assistant', content: '**HBM** 带宽更高' },
    { role: 'user', content: '缺点呢？' },
  ]);
});

it('keeps the question and offers retry when the request fails', async () => {
  const send = vi.spyOn(chatApi, 'send').mockRejectedValueOnce(new Error('超时')).mockResolvedValueOnce({ reply: '好了' });
  await act(async () => root.render(<ChatFeature />));
  await type('你好');
  expect(host.textContent).toContain('没拿到回复：超时');
  const retry = Array.from(host.querySelectorAll('button')).find(b => b.textContent?.includes('重试'))!;
  await act(async () => retry.click());
  expect(send).toHaveBeenCalledTimes(2);
  expect(host.textContent).toContain('好了');
});
