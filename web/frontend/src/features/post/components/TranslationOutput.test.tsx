// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import { TranslationOutput } from './TranslationOutput';

async function counterFor(content: string) {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div');
  const root = createRoot(host);
  try {
    await act(async () => root.render(<TranslationOutput
      versions={[]} currentVersionId={null} originalText="" currentContent={content}
      isEdited={false} editedContent="" onSetCurrentVersion={vi.fn()} onSetEditedContent={vi.fn()}
      onSaveEdit={vi.fn()} onDiscardEdit={vi.fn()}
    />));
    return Array.from(host.querySelectorAll('span')).find(span => /^\d[\d,]*\/1,000$/.test(span.textContent ?? ''));
  } finally {
    act(() => root.unmount());
  }
}

it('shows the count against the 1,000 target and only flags, never truncates, longer translations', async () => {
  const short = await counterFor('字'.repeat(887));
  expect(short?.textContent).toBe('887/1,000');
  expect(short?.className).toContain('text-text-muted');
  expect(short?.title).toBe('');

  const long = await counterFor('字'.repeat(1_200));
  expect(long?.textContent).toBe('1,200/1,000');
  expect(long?.className).toContain('text-warning');
  expect(long?.title).toBe('超过建议的 1,000 字');
});
