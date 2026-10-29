// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { findClaudeOutputs } from './claude';
import { gridTemplate, loadCollapsed, NONE_COLLAPSED, togglePane } from './panes';
import { countFilled, sectionsWithMissing } from './tracks';
import type { WorkbenchRow } from '../types';

const row = (key: string, kind: string, web: string | null): WorkbenchRow => ({ key, kind, section_id: 's', paragraph_id: key, source: key, web, alt: {} });

describe('panes', () => {
  it('collapses any pane but always keeps one open', () => {
    let state = togglePane(NONE_COLLAPSED, 'source');
    state = togglePane(state, 'compare');
    expect(state).toEqual({ source: true, main: false, compare: true });
    expect(togglePane(state, 'main')).toBe(state);
    expect(gridTemplate(state)).toBe('36px minmax(0, 1fr) 36px');
  });

  it('reads collapsed panes saved under the old web / alt keys', () => {
    localStorage.setItem('momo.workbench.collapsed', JSON.stringify({ source: false, web: false, alt: true }));
    expect(loadCollapsed()).toEqual({ source: false, main: false, compare: true });
    localStorage.removeItem('momo.workbench.collapsed');
  });
});

describe('findClaudeOutputs', () => {
  it('takes the newest zh.md that has an en.md next to it', () => {
    const files = [
      { path: 'output/old/zh.md', size: 1, mtime: 10 },
      { path: 'output/old/en.md', size: 1, mtime: 10 },
      { path: 'output/new/zh.md', size: 1, mtime: 20 },
      { path: 'output/new/en.md', size: 1, mtime: 20 },
      { path: 'stray/zh.md', size: 1, mtime: 30 },
    ];
    expect(findClaudeOutputs(files)).toEqual({ zh: 'output/new/zh.md', en: 'output/new/en.md' });
    expect(findClaudeOutputs([{ path: 'notes.md', size: 1, mtime: 1 }])).toBeNull();
  });
});

describe('countFilled', () => {
  it('counts filled paragraphs without images', () => {
    const rows = [row('a', 'p', '一'), row('b', 'image', null), row('c', 'p', null)];
    const filled = countFilled(rows, item => item.web);
    expect(filled).toEqual({ done: 1, total: 2 });
  });
});

describe('sectionsWithMissing', () => {
  it('lists each section that still has untranslated paragraphs once, in order, ignoring images and headings', () => {
    const rows: WorkbenchRow[] = [
      { ...row('section:s1', 'section', '一'), section_id: 's1', source: 'Intro' },
      { ...row('s1/p1', 'p', null), section_id: 's1' },
      { ...row('s1/p2', 'p', null), section_id: 's1' },
      { ...row('s2/p1', 'image', null), section_id: 's2' },
      { ...row('s3/p1', 'p', '有'), section_id: 's3' },
    ];
    expect(sectionsWithMissing(rows, item => item.web)).toEqual([{ id: 's1', title: 'Intro' }]);
  });
});
