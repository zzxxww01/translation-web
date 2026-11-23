// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import type { DraftSummary } from '../drafts';

const useDraftList = vi.fn();
vi.mock('../drafts', () => ({ useDraftList: (...args: unknown[]) => useDraftList(...args) }));

const { DraftHistory } = await import('./DraftHistory');

function item(id: string, extra: Partial<DraftSummary>): DraftSummary {
  return {
    id, source: 'manual', status: 'draft', auto: false, seen: true, title: id, preview: '译文', source_preview: '',
    versions: 1, images: [], image_count: 0, slack: null, created_at: 1, updated_at: 1, ...extra,
  };
}

it('shows sent / unsent and filters by it', async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  useDraftList.mockReturnValue({
    isLoading: false,
    data: [
      item('a', { sent: false, status: 'done' }),
      item('b', { sent: true, sent_at: 100 }),
      item('c', { sent: true, sent_at: null, sent_auto: true }),
    ],
  });
  const host = document.createElement('div');
  const root = createRoot(host);
  try {
    await act(async () => root.render(<DraftHistory activeId={null} onOpen={vi.fn()} />));
    expect(host.textContent).toContain('未发送 · 已完成');
    expect(host.textContent).toContain('已发送（超过两周）');
    expect(useDraftList).toHaveBeenLastCalledWith('', '');

    const unsent = Array.from(host.querySelectorAll('button')).find(b => b.textContent === '未发送')!;
    await act(async () => unsent.click());
    expect(useDraftList).toHaveBeenLastCalledWith('', 'no');
    expect(unsent.getAttribute('aria-pressed')).toBe('true');
  } finally {
    await act(async () => root.unmount());
    vi.unstubAllGlobals();
  }
});
