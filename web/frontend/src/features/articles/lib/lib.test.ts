// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { findClaudeOutputs } from './claude';
import { gridTemplate, loadCollapsed, NONE_COLLAPSED, togglePane } from './panes';
import { countFilled, sectionsWithMissing, trackSummary } from './tracks';
import type { TrackStatus, WorkbenchRow } from '../types';

const idle: TrackStatus = { active: false, run_id: null, status: null, current_step: null, translated: null, total: null, error: null };
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

describe('track summary', () => {
  it('counts filled paragraphs without images and names the waiting step', () => {
    const rows = [row('a', 'p', '一'), row('b', 'image', null), row('c', 'p', null)];
    const filled = countFilled(rows, item => item.web);
    expect(filled).toEqual({ done: 1, total: 2 });
    expect(trackSummary({ ...idle, active: true, current_step: '等待术语确认' }, filled)).toEqual({ text: '等你确认术语', tone: 'wait' });
    expect(trackSummary({ ...idle, active: true, current_step: '翻译章节' }, filled).text).toBe('翻译章节 1/2');
    expect(trackSummary({ ...idle, active: true, current_step: '处理中: The shape of the buildout' }, filled).text).toBe('处理中 1/2');
    expect(trackSummary(idle, filled)).toEqual({ text: '缺 1 段', tone: 'wait' });
    expect(trackSummary(idle, { done: 2, total: 2 }).text).toBe('已完成');
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
