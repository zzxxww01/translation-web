// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import { TitleGenerator } from './TitleGenerator';

it('counts Unicode code points and flags old saved overlong titles instead of accepting them', async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div');
  const root = createRoot(host);
  const onSelectTitle = vi.fn();
  const valid = '中A1 !😀' + '文'.repeat(14);
  const titles = [valid, valid + '!', '😀'.repeat(20), '😀'.repeat(21)];
  try {
    await act(async () => root.render(<TitleGenerator
      onGenerate={vi.fn()} isLoading={false} isGenerating={false} canGenerate
      contentIdentity="new" titlesContentIdentity="old" titles={titles}
      selectedTitle={titles[1]} onSelectTitle={onSelectTitle}
    />));
    const buttons = Array.from(host.querySelectorAll('button')).filter(button => button.title.includes('标题'));
    expect(buttons).toHaveLength(4);
    for (const index of [0, 2]) {
      expect(buttons[index].textContent).toContain('20/20 字');
      expect(buttons[index].disabled).toBe(false);
    }
    for (const index of [1, 3]) {
      expect(buttons[index].textContent).toContain('21/20 字 · 超限');
      expect(buttons[index].disabled).toBe(true);
      await act(async () => buttons[index].click());
    }
    expect(onSelectTitle).not.toHaveBeenCalled();
    expect(host.textContent).toContain('内容已变更');
  } finally {
    await act(async () => root.unmount());
    vi.unstubAllGlobals();
  }
});
