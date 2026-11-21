// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ResizablePanes } from './ResizablePanes';

let host: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  vi.stubGlobal('innerWidth', 1440);
  localStorage.clear();
  host = document.createElement('div');
  root = createRoot(host);
});
afterEach(async () => {
  await act(async () => root.unmount());
  vi.unstubAllGlobals();
});

const panes = [
  { id: 'a', title: '原文', width: 300, content: <p>source</p> },
  { id: 'b', title: '译文', content: <p>work</p> },
  { id: 'c', title: 'thread', width: 280, content: <p>thread</p> },
];

it('closes a pane into a strip, reopens it, and remembers the layout', async () => {
  await act(async () => root.render(<ResizablePanes panes={panes} storageKey="t" />));
  expect(host.querySelectorAll('section')).toHaveLength(3);
  expect(host.querySelectorAll('[role="separator"]')).toHaveLength(2);
  await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="收起「thread」"]')!.click());
  expect(host.querySelectorAll('section')).toHaveLength(2);
  expect(JSON.parse(localStorage.getItem('t')!).closed).toEqual(['c']);
  const strip = host.querySelector<HTMLButtonElement>('[title="展开「thread」"]')!;
  expect(strip.textContent).toBe('thread');
  await act(async () => strip.click());
  expect(host.querySelectorAll('section')).toHaveLength(3);
  // 最后一栏不能也收起
  await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="收起「原文」"]')!.click());
  await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="收起「thread」"]')!.click());
  await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="收起「译文」"]')!.click());
  expect(host.querySelectorAll('section')).toHaveLength(1);
  // 没写 width 的那栏占剩余空间
  expect((host.querySelector('[data-pane="b"]') as HTMLElement).style.flex).toContain('1 1');
});

it('uses tabs on narrow screens and starts on the requested pane', async () => {
  vi.stubGlobal('innerWidth', 375);
  await act(async () => root.render(<ResizablePanes panes={panes} storageKey="t" mobileDefault="b" />));
  expect(host.querySelectorAll('[role="tab"]')).toHaveLength(3);
  expect(host.textContent).toContain('work');
  expect(host.textContent).not.toContain('source');
});
