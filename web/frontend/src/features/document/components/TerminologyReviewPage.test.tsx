// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { TermReviewCandidate, TermReviewPayload } from '../../confirmation/types';
import { TerminologyReviewPage } from './TerminologyReviewPage';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const candidate = (term: string, suggested: string, over: Partial<TermReviewCandidate> = {}): TermReviewCandidate => ({
  term, suggested_translation: suggested, reasons: ['high_frequency'], occurrence_count: 3,
  related_sections: [{ section_id: 's1', section_title: 'Intro' }], contexts: [`The ${term} is large.`], similar_terms: [], ...over,
});

const review: TermReviewPayload = {
  artifact_id: 'a', project_id: 'p', project_title: 'Demo', review_required: true, generated_at: '', total_candidates: 3,
  sections: [{ section_id: 's1', section_title: 'Intro', candidates: [
    candidate('CoWoS', 'CoWoS'),
    candidate('hyperscaler', '超大规模云厂商', { similar_terms: [{ original: 'hyperscalers', translation: '云巨头', strategy: 'translate', scope: 'global', similarity: 0.9 }] }),
    candidate('neocloud', '新云'),
  ] }],
};

let host: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
beforeEach(() => {
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
});

const input = (term: string) => host.querySelector<HTMLInputElement>(`[aria-label="${term} 的译法"]`)!;
const type = (el: HTMLInputElement, value: string) => {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(el, value);
  el.dispatchEvent(new Event('input', { bubbles: true }));
};

it('shows each term with count, first section, highlighted context, and maps edits to accept / custom / skip', async () => {
  const onSubmit = vi.fn();
  await act(async () => root.render(<TerminologyReviewPage review={review} onSubmit={onSubmit} onCancel={vi.fn()} />));
  expect(host.textContent).toContain('3 个术语等你定译法');
  expect(host.textContent).toContain('出现 3 次 · 首次在「Intro」 · 高频');
  expect(host.querySelector('mark')?.textContent).toBe('CoWoS');
  expect(input('CoWoS').value).toBe('CoWoS');

  // 点术语表里相近的词 = 用它的译法
  await act(async () => (Array.from(host.querySelectorAll('button')).find(b => b.textContent === 'hyperscalers → 云巨头') as HTMLButtonElement).click());
  expect(input('hyperscaler').value).toBe('云巨头');
  expect(host.textContent).toContain('建议是「超大规模云厂商」');

  const skip = input('neocloud').closest('li')!.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  await act(async () => skip.click());
  expect(input('neocloud').disabled).toBe(true);
  expect(host.textContent).toContain('改了 2 个');

  await act(async () => (Array.from(host.querySelectorAll('button')).find(b => b.textContent === '确认，继续翻译') as HTMLButtonElement).click());
  expect(onSubmit.mock.calls[0][0]).toEqual([
    { term: 'CoWoS', action: 'accept', translation: 'CoWoS', first_occurrence: 's1' },
    { term: 'hyperscaler', action: 'custom', translation: '云巨头', first_occurrence: 's1' },
    { term: 'neocloud', action: 'skip', translation: undefined, first_occurrence: 's1' },
  ]);
});

it('blocks submit while a term has no translation', async () => {
  await act(async () => root.render(<TerminologyReviewPage review={review} onSubmit={vi.fn()} onCancel={vi.fn()} />));
  await act(async () => type(input('CoWoS'), ''));
  expect(host.textContent).toContain('1 个术语没填译法');
  expect((Array.from(host.querySelectorAll('button')).find(b => b.textContent === '确认，继续翻译') as HTMLButtonElement).disabled).toBe(true);
});
