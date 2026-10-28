import { describe, expect, it } from 'vitest';
import type { RunMeta } from '@/features/skills/types';
import type { TrackStatus, Workbench, WorkbenchVariant } from '../types';
import { buildVersions, defaultCompare, pickPrimary } from './versions';

const idle: TrackStatus = { active: false, run_id: null, status: null, current_step: null, translated: null, total: null, error: null };
const variant = (id: string, over: Partial<WorkbenchVariant> = {}): WorkbenchVariant => ({
  id, kind: 'claude', label: 'Codex', title_translation: null, progress: { total: 2, approved: 0 }, status: idle, import: null, ...over,
});
const imported = (agent: 'claude' | 'codex' | 'antigravity', model: string | null, at: string, run = 'r0') =>
  ({ run_id: run, agent, model, aligned: 2, unaligned: 0, merged_blocks: 0, imported_at: at });
const data = (over: Partial<Workbench> = {}, web: (string | null)[] = ['一', '二']): Workbench => ({
  project: { id: 'p', title: 'T', title_translation: null, original_url: null, created_at: '', claude_run_id: null,
    progress: { total: 2, approved: 0 }, status: idle },
  variants: [],
  rows: web.map((text, i) => ({ key: `s/p${i}`, kind: 'p', section_id: 's', paragraph_id: `p${i}`, source: `S${i}`, web: text,
    alt: { 'p--codex': `码${i}`, 'p--claude': `克${i}`, 'p--argon': i ? null : '氩' } })),
  ...over,
});
const run = (over: Partial<RunMeta>): RunMeta => ({ id: 'r1', skill: 'four-step-translate', title: 't', status: 'running',
  created_at: 0, updated_at: 0, session_id: null, error: null, harness: 'codex', ...over });
const build = (d: Workbench, r?: RunMeta, extra: { needsLogin?: boolean; importProblem?: { runId: string; message: string; alignment: boolean } } = {}) =>
  buildVersions({ data: d, run: r, needsLogin: extra.needsLogin ?? false, importProblem: extra.importProblem ?? null });

describe('buildVersions', () => {
  it('orders web, agents (Codex first) and model versions, and names Gemini', () => {
    const { versions, addable } = build(data({ variants: [
      variant('p--argon', { kind: 'model', label: 'argon' }),
      variant('p--claude', { label: 'Claude', import: imported('claude', 'opus', '2026-10-28T09:00:00') }),
      variant('p--antigravity', { label: 'Antigravity', import: null }),
      variant('p--codex', { import: imported('codex', 'gpt-5.5', '2026-10-28T10:00:00') }),
    ] }));
    expect(versions.map(v => [v.id, v.name])).toEqual([
      ['p', '网页版'], ['p--codex', 'Codex'], ['p--claude', 'Claude'], ['p--antigravity', 'Gemini'], ['p--argon', 'argon'],
    ]);
    expect(addable).toEqual([]);
    expect(versions[1]).toMatchObject({ source: 'agent', harness: 'codex', model: 'gpt-5.5', tone: 'done', translate: 'retranslate',
      line: ['已完成', 'gpt-5.5'] });
  });

  it('gives the web version continue only when it is unfinished', () => {
    expect(build(data()).versions[0]).toMatchObject({ tone: 'done', line: ['已完成'], translate: 'none', actions: [] });
    expect(build(data({}, ['一', null])).versions[0]).toMatchObject({
      tone: 'wait', line: ['缺 1 段'], translate: 'continue', actions: [{ kind: 'continue', label: '继续翻译' }] });
    expect(build(data({}, [null, null])).versions[0]).toMatchObject({
      tone: 'idle', line: ['还没开始'], actions: [{ kind: 'continue', label: '开始翻译' }] });
    const terms = data({}, [null, null]);
    terms.project.status = { ...idle, active: true, current_step: '等待术语确认', run_id: 'job' };
    expect(build(terms).versions[0]).toMatchObject({ tone: 'wait', translate: 'none',
      actions: [{ kind: 'confirm-terms', label: '去确认', jobId: 'job' }] });
    const failed = data({}, ['一', null]);
    failed.project.status = { ...idle, error: '额度用完' };
    expect(build(failed).versions[0]).toMatchObject({ tone: 'wait', line: ['缺 1 段'], translate: 'continue',
      actions: [{ kind: 'continue', label: '继续翻译' }] });
    const stale = data();
    stale.project.status = { ...idle, error: '旧错误' };
    expect(build(stale).versions[0]).toMatchObject({ tone: 'done', line: ['已完成'], translate: 'none', actions: [] });
  });

  it('shows a first-time agent as pending and a re-translated one as read only', () => {
    const first = build(data(), run({ harness: 'antigravity', actual_model: 'gemini-3.8-pro' }));
    expect(first.versions.map(v => v.id)).toEqual(['p', 'p--antigravity']);
    expect(first.versions[1]).toMatchObject({ pending: true, readOnly: false, tone: 'busy', model: 'gemini-3.8-pro',
      line: ['翻译中', 'gemini-3.8-pro'], actions: [{ kind: 'open-run', label: '看对话' }] });
    expect(first.addable).toEqual(['codex', 'claude']);

    const again = build(data({ variants: [variant('p--codex', { import: imported('codex', 'gpt-5.5', 'x') })] }),
      run({ model: 'gpt-5.5-codex' }));
    expect(again.versions[1]).toMatchObject({ readOnly: true, tone: 'busy', line: ['重翻中', 'gpt-5.5-codex', '翻完前只读'] });
  });

  it('reports waiting, failed and mismatched agent runs', () => {
    const waiting = build(data(), run({ status: 'idle', awaiting_reply: true, auto_reply_at: Date.UTC(2026, 9, 28, 6, 30) / 1000 }));
    expect(waiting.versions[1].tone).toBe('wait');
    expect(waiting.versions[1].line[0]).toBe('等你确认');
    expect(waiting.versions[1].line[1]).toMatch(/前不回复就按它的建议继续$/);
    expect(waiting.versions[1].actions).toEqual([{ kind: 'open-run', label: '去确认' }]);

    const failed = build(data(), run({ status: 'error', error: '模型 ID 不存在' }));
    expect(failed.versions[1]).toMatchObject({ tone: 'error', line: ['出错了：模型 ID 不存在'] });

    const mismatch = build(data(), run({ status: 'idle' }),
      { importProblem: { runId: 'r1', message: 'Agent 的英文稿只对上 1/3 段，可能不是这篇下载的原文', alignment: true } });
    expect(mismatch.versions[1]).toMatchObject({ tone: 'error',
      line: ['没导入：Agent 的英文稿只对上 1/3 段，可能不是这篇下载的原文'],
      actions: [{ kind: 'open-run', label: '看对话' }, { kind: 'force-import', label: '仍然导入' }] });
  });

  it('treats an imported run as done and an unknown run (needs login) as a login prompt', () => {
    const done = build(data({ variants: [variant('p--codex', { import: imported('codex', 'gpt-5.5', 'x', 'r1') })] }),
      run({ status: 'idle' }));
    expect(done.versions[1]).toMatchObject({ tone: 'done', readOnly: false, pending: false });

    const login = build(data({ project: { ...data().project, claude_run_id: 'r9' } }), undefined, { needsLogin: true });
    expect(login.versions[1]).toMatchObject({ name: 'Agent', harness: null, translate: 'none',
      actions: [{ kind: 'login', label: '去登录' }] });
  });

  it('offers continue for a model version with gaps, using its model', () => {
    const { versions } = build(data({ variants: [variant('p--argon', { kind: 'model', label: 'argon' })] }));
    expect(versions[1]).toMatchObject({ source: 'model', translate: 'continue', fillModel: 'gemini-official-argon', line: ['缺 1 段'] });
  });
});

describe('review fixes', () => {
  const codex = () => variant('p--codex', { import: imported('codex', 'gpt-5.5', 'x', 'r1') });

  it('keeps finished agent versions normal when the login prompt is needed for an unknown run', () => {
    const d = data({ variants: [codex()], project: { ...data().project, claude_run_id: 'r9' } });
    const { versions } = build(d, undefined, { needsLogin: true });
    expect(versions.find(v => v.id === 'p--codex')).toMatchObject({ tone: 'done', line: ['已完成', 'gpt-5.5'], actions: [] });
    expect(versions.find(v => v.harness === null && v.source === 'agent')?.actions).toEqual([{ kind: 'login', label: '去登录' }]);
  });

  it('ignores the login prompt when the run is already imported', () => {
    const d = data({ variants: [codex()], project: { ...data().project, claude_run_id: 'r1' } });
    const { versions } = build(d, undefined, { needsLogin: true });
    expect(versions.map(v => v.id)).toEqual(['p', 'p--codex']);
    expect(versions[1].line).toEqual(['已完成', 'gpt-5.5']);
  });

  it('keeps the imported model on a failed re-translation, which stays editable', () => {
    const d = data({ variants: [codex()] });
    const failed = build(d, run({ id: 'r2', status: 'error', error: '模型 ID 不存在', model: 'bad-id' })).versions[1];
    expect(failed).toMatchObject({ model: 'gpt-5.5', readOnly: false, tone: 'error', line: ['出错了：模型 ID 不存在'] });
    const again = build(d, run({ id: 'r2', model: 'bad-id' })).versions[1];
    expect(again).toMatchObject({ model: 'gpt-5.5', line: ['重翻中', 'bad-id', '翻完前只读'] });
  });

  it('says read only while a re-translation waits for confirmation', () => {
    const d = data({ variants: [codex()] });
    const waiting = build(d, run({ id: 'r2', status: 'idle', awaiting_reply: true })).versions[1];
    expect(waiting.line).toContain('翻完前只读');
    expect(waiting.readOnly).toBe(true);
  });

  it('offers continue for an empty model version and none for a complete one', () => {
    const empty = data({ variants: [variant('p--argon', { kind: 'model', label: 'argon' })] }, [null, null]);
    empty.rows.forEach(r => { r.alt['p--argon'] = null; });
    expect(build(empty).versions[1]).toMatchObject({ translate: 'continue', line: ['缺 2 段'], actions: [{ kind: 'continue', label: '继续翻译' }] });
    const full = data({ variants: [variant('p--argon', { kind: 'model', label: 'argon' })] });
    full.rows.forEach(r => { r.alt['p--argon'] = 'x'; });
    expect(build(full).versions[1]).toMatchObject({ translate: 'none', tone: 'done' });
  });

  it('has no translate button on a running web version', () => {
    const d = data({}, ['一', null]);
    d.project.status = { ...idle, active: true, current_step: '翻译中', run_id: 'job' };
    expect(build(d).versions[0]).toMatchObject({ tone: 'busy', translate: 'none', actions: [] });
  });

  it('offers retranslate for a first run that never produced a version, with nothing to replace', () => {
    const v = build(data(), run({ status: 'error', error: 'x' })).versions[1];
    expect(v).toMatchObject({ pending: true, variant: null, translate: 'retranslate' });
  });

  it('does not offer force-import when the problem is not an alignment mismatch', () => {
    const v = build(data(), run({ status: 'idle' }),
      { importProblem: { runId: 'r1', message: '没找到 zh.md', alignment: false } }).versions[1];
    expect(v).toMatchObject({ tone: 'error', line: ['没导入：没找到 zh.md'], actions: [{ kind: 'open-run', label: '看对话' }] });
  });
});

describe('primary and compare', () => {
  const d = data({ variants: [
    variant('p--claude', { label: 'Claude', import: imported('claude', 'opus', '2026-10-28T09:00:00') }),
    variant('p--codex', { import: imported('codex', 'gpt-5.5', '2026-10-28T10:00:00') }),
    variant('p--argon', { kind: 'model', label: 'argon' }),
  ] });

  it('uses the primary from the server and falls back to the web version', () => {
    const { versions } = build(d);
    expect(pickPrimary(versions, 'p--claude').id).toBe('p--claude');
    expect(pickPrimary(versions, 'p--gone').id).toBe('p');
    expect(pickPrimary(versions, undefined).id).toBe('p');
  });

  it('compares against the live run first, then the latest import', () => {
    const { versions } = build(d);
    expect(defaultCompare(versions, versions[0])?.id).toBe('p--codex');
    expect(defaultCompare(versions, versions[1])?.id).toBe('p--claude');
    const live = build(d, run({ harness: 'antigravity' }));
    expect(defaultCompare(live.versions, live.versions[0], run({ harness: 'antigravity' }))?.id).toBe('p--antigravity');
    expect(defaultCompare(build(data()).versions, build(data()).versions[0])).toBeNull();
    // 正在跑的 Agent 就是主译本：对照别的版本
    const agentPrimary = build(d, run({ harness: 'codex', id: 'r2' }));
    expect(defaultCompare(agentPrimary.versions, agentPrimary.versions.find(v => v.id === 'p--codex')!, run({ harness: 'codex', id: 'r2' }))?.id)
      .toBe('p--claude');
  });
});
