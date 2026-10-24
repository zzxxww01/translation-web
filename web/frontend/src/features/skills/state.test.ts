// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { foldEvents, formatBytes, formatDuration, mergeEvents, runKindLabel } from './state';
import { renderMarkdown } from './markdown';
import { isStalled, STALL_MS } from './hooks';
import type { SkillEvent } from './types';

let seq = 0;
const ev = (event: Record<string, unknown>) => ({ seq: ++seq, ts: 0, ...event }) as SkillEvent;

describe('foldEvents', () => {
  it('groups consecutive tool calls and nests subagent calls under their parent', () => {
    seq = 0;
    const view = foldEvents([
      ev({ type: 'user', text: '翻译', files: ['input/a.html'] }),
      ev({ type: 'status', status: 'running', error: null }),
      ev({ type: 'tool', id: 'a', name: 'Read', summary: 'input/a.html', parent: null }),
      ev({ type: 'tool', id: 'b', name: 'Agent', summary: '翻译第 1 段', parent: null }),
      ev({ type: 'tool', id: 'c', name: 'Write', summary: 'chunks/1.md', parent: 'b' }),
      ev({ type: 'tool_result', id: 'c', ok: true, text: 'ok', parent: 'b' }),
      ev({ type: 'tool_result', id: 'a', ok: false, text: 'boom', parent: null }),
      ev({ type: 'text', text: '子代理文字不展示', parent: 'b' }),
      ev({ type: 'text', text: '术语表如下', parent: null }),
      ev({ type: 'tool', id: 'd', name: 'Bash', summary: 'qa', parent: null }),
    ]);
    expect(view.items.map(item => item.kind)).toEqual(['user', 'tools', 'text', 'tools']);
    const group = view.items[1];
    if (group.kind !== 'tools') throw new Error('expected tools');
    expect(group.tools.map(t => t.id)).toEqual(['a', 'b']);
    expect(group.tools[0].result).toEqual({ ok: false, text: 'boom' });
    expect(group.tools[1].children.map(t => [t.id, t.result?.ok])).toEqual([['c', true]]);
    expect(view.status).toBe('running');
    expect(view.lastSeq).toBe(10);
  });

  it('tracks questions until answered and drops stale ones after an interruption', () => {
    seq = 0;
    const asked = [
      ev({ type: 'question', qid: 'q1', questions: [{ question: '术语表可以吗？', options: [{ label: '确认' }] }] }),
      ev({ type: 'status', status: 'waiting', error: null }),
    ];
    expect(foldEvents(asked).pendingQids).toEqual(['q1']);

    const answered = foldEvents([...asked, ev({ type: 'answer', qid: 'q1', answers: { '术语表可以吗？': '确认' } })]);
    expect(answered.pendingQids).toEqual([]);
    const item = answered.items[0];
    if (item.kind !== 'question') throw new Error('expected question');
    expect(item.answer?.answers).toEqual({ '术语表可以吗？': '确认' });

    const interrupted = foldEvents([...asked, ev({ type: 'status', status: 'error', error: '服务重启' })]);
    expect(interrupted.pendingQids).toEqual([]);
    expect(interrupted.error).toBe('服务重启');
  });

  it('keeps the latest todo list and turns results, notices and errors into items', () => {
    seq = 0;
    const view = foldEvents([
      ev({ type: 'todos', items: [{ content: '理解', status: 'completed' }] }),
      ev({ type: 'todos', items: [{ content: '理解', status: 'completed' }, { content: '翻译', status: 'in_progress' }] }),
      ev({ type: 'notice', level: 'warn', text: '额度提醒' }),
      ev({ type: 'error', text: '进程退出' }),
      ev({ type: 'result', is_error: false, subtype: 'success', duration_ms: 65_000, num_turns: 4, errors: [] }),
    ]);
    expect(view.todos).toHaveLength(2);
    expect(view.items.map(item => item.kind === 'notice' ? `${item.kind}:${item.level}` : item.kind)).toEqual([
      'notice:warn',
      'notice:error',
      'turn',
    ]);
  });
});

describe('mergeEvents', () => {
  it('drops replayed events and keeps order', () => {
    const a = { seq: 1, ts: 0, type: 'error', text: 'a' } as SkillEvent;
    const b = { seq: 2, ts: 0, type: 'error', text: 'b' } as SkillEvent;
    const c = { seq: 3, ts: 0, type: 'error', text: 'c' } as SkillEvent;
    const merged = mergeEvents([a, b], [b, c]);
    expect(merged.map(e => e.seq)).toEqual([1, 2, 3]);
    const unchanged = [a, b];
    expect(mergeEvents(unchanged, [a])).toBe(unchanged);
  });
});

describe('formatting', () => {
  it('formats sizes and durations', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(5 * 1024 ** 3)).toBe('5.00 GB');
    expect(formatDuration(42_000)).toBe('42 秒');
    expect(formatDuration(125_000)).toBe('2 分 5 秒');
    expect(formatDuration(3_725_000)).toBe('1 小时 2 分');
  });

  it('labels runs without a skill as direct chat', () => {
    expect(runKindLabel('four-step-translate')).toBe('four-step-translate');
    expect(runKindLabel('')).toBe('直接对话');
  });
});

describe('isStalled', () => {
  it('treats a stream as stuck only after two missed server pings and then some', () => {
    // 服务端每 15 秒一次心跳，阈值要留出余量，又不能让卡住的页面等太久
    expect(STALL_MS).toBeGreaterThan(2 * 15_000);
    expect(STALL_MS).toBeLessThanOrEqual(60_000);
    expect(isStalled(0, STALL_MS)).toBe(false);
    expect(isStalled(0, STALL_MS + 1)).toBe(true);
  });
});

describe('renderMarkdown', () => {
  it('renders GFM tables and strips scripts, handlers and images', () => {
    const html = renderMarkdown('| 英文 | 中文 |\n|---|---|\n| fleet | 机队 |\n\n<script>alert(1)</script><a href="javascript:x" onclick="y">x</a><img src=x onerror=z>');
    expect(html).toContain('<table>');
    expect(html).toContain('<td>机队</td>');
    expect(html).not.toMatch(/script|onclick|onerror|javascript:|<img/i);
  });
});
