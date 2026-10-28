/**
 * 工作台里每一版译文的视图模型：叫什么、谁翻的、用什么模型、现在什么状态、状态行写什么、能做什么。
 * 组件只按这里的结果显示，判断都集中在这里（设计文档 4.3、6.3）。
 */
import { harnessLabel, type Harness } from '@/features/skills/harness';
import type { RunMeta } from '@/features/skills/types';
import type { TrackStatus, Workbench, WorkbenchRow, WorkbenchVariant } from '../types';
import { ARTICLE_HARNESSES } from './agentChoice';
import { countFilled, SECOND_MODELS, shortStep, TERMS_STEP } from './tracks';

export type Tone = 'done' | 'busy' | 'wait' | 'error' | 'idle';

export type VersionAction =
  | { kind: 'confirm-terms'; label: string; jobId: string }
  | { kind: 'open-run'; label: string }
  | { kind: 'continue'; label: string }
  | { kind: 'login'; label: string }
  | { kind: 'force-import'; label: string };

/** 栏头的翻译按钮：没有 / 继续翻译（写在状态行里）/ 重新翻译（只换模型） */
export type TranslateButton = 'none' | 'continue' | 'retranslate';

export interface VersionView {
  /** 主项目或孪生项目 id；还没导入的 Agent 版用 `${主id}--${harness}`，和导入后的 id 一致 */
  id: string;
  source: 'web' | 'agent' | 'model';
  harness: Harness | null;
  name: string;
  model: string | null;
  tone: Tone;
  /** 状态行的几段，用「 · 」连起来；行动链接另放在 actions */
  line: string[];
  actions: VersionAction[];
  readOnly: boolean;
  translate: TranslateButton;
  /** Agent 正在跑、还没有译文 */
  pending: boolean;
  variant: WorkbenchVariant | null;
  /** 模型版「继续翻译」时用的模型 */
  fillModel?: string;
  text: (row: WorkbenchRow) => string | null;
}

export interface ImportProblem {
  runId: string;
  message: string;
  /** 英文稿和下载的原文对不上（可以「仍然导入」） */
  alignment: boolean;
}

export interface VersionsInput {
  data: Workbench;
  run?: RunMeta;
  /** 这篇有 Agent 对话，但浏览器还没登录 Agent 页（查 run 得到 401） */
  needsLogin: boolean;
  importProblem: ImportProblem | null;
}

const clock = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });
const LABEL_HARNESS: Record<string, Harness> = { Claude: 'claude', Codex: 'codex', Antigravity: 'antigravity', Gemini: 'antigravity' };
const AGENT_ORDER: Harness[] = ARTICLE_HARNESSES.map(item => item.id);

export function variantHarness(variant: WorkbenchVariant): Harness | null {
  if (variant.kind !== 'claude') return null;
  return variant.import?.agent ?? LABEL_HARNESS[variant.label] ?? 'claude';
}

const runHarness = (run: RunMeta): Harness => run.harness ?? 'claude';
const isWaiting = (run: RunMeta) => run.status === 'waiting' || Boolean(run.status === 'idle' && run.awaiting_reply);
/** 正在跑或在等你确认 */
export const runActive = (run?: RunMeta) => Boolean(run && (run.status === 'running' || isWaiting(run)));

type TrackState = Pick<VersionView, 'tone' | 'line' | 'actions' | 'translate'>;

/** 网页版和模型版：后台四步法的状态 */
function trackState(status: TrackStatus, filled: { done: number; total: number }, canStart: boolean): TrackState {
  if (status.active) {
    if (status.current_step === TERMS_STEP && status.run_id) {
      return { tone: 'wait', line: ['等你确认术语', '10 分钟内不确认会自动采用建议'],
        actions: [{ kind: 'confirm-terms', label: '去确认', jobId: status.run_id }], translate: 'none' };
    }
    return { tone: 'busy', line: [`${shortStep(status.current_step)} ${filled.done}/${filled.total}`], actions: [], translate: 'none' };
  }
  const partial = filled.done > 0 && filled.done < filled.total;
  const resume: VersionAction[] = partial ? [{ kind: 'continue', label: '继续翻译' }]
    : filled.done === 0 && canStart ? [{ kind: 'continue', label: '开始翻译' }] : [];
  const translate: TranslateButton = resume.length ? 'continue' : 'none';
  if (status.error) return { tone: 'error', line: [`出错了：${status.error}`], actions: resume, translate };
  if (filled.total && filled.done >= filled.total) return { tone: 'done', line: ['已完成'], actions: [], translate: 'none' };
  if (partial) return { tone: 'wait', line: [`缺 ${filled.total - filled.done} 段`], actions: resume, translate };
  return { tone: 'idle', line: [canStart ? '还没开始' : '还没有译文'], actions: resume, translate };
}

function webVersion({ project, rows }: Workbench): VersionView {
  const text = (row: WorkbenchRow) => row.web;
  return {
    id: project.id, source: 'web', harness: null, name: '网页版', model: null, readOnly: false, pending: false, variant: null, text,
    ...trackState(project.status, countFilled(rows, text), true),
  };
}

function modelVersion(variant: WorkbenchVariant, rows: WorkbenchRow[]): VersionView {
  const text = (row: WorkbenchRow) => row.alt[variant.id] ?? null;
  return {
    id: variant.id, source: 'model', harness: null, name: variant.label, model: null, readOnly: false, pending: false, variant, text,
    fillModel: SECOND_MODELS.find(option => option.label === variant.label)?.model,
    ...trackState(variant.status, countFilled(rows, text), false),
  };
}

function agentVersion(input: VersionsInput, harness: Harness, variant: WorkbenchVariant | null): VersionView {
  const { data, run, needsLogin, importProblem } = input;
  const text = (row: WorkbenchRow) => (variant ? row.alt[variant.id] ?? null : null);
  const base = {
    id: variant?.id ?? `${data.project.id}--${harness}`, source: 'agent' as const, harness, name: harnessLabel(harness),
    variant, pending: !variant, text, translate: 'retranslate' as const,
  };
  const own = run && runHarness(run) === harness && variant?.import?.run_id !== run.id ? run : undefined;
  if (own) {
    const model = own.actual_model ?? own.model ?? null;
    const withModel = (...parts: (string | null)[]) => parts.filter((part): part is string => Boolean(part));
    if (isWaiting(own)) {
      const at = own.auto_reply_at ? `${clock.format(own.auto_reply_at * 1000)} 前不回复就按它的建议继续` : null;
      return { ...base, model, tone: 'wait', line: withModel('等你确认', at), actions: [{ kind: 'open-run', label: '去确认' }], readOnly: Boolean(variant) };
    }
    if (own.status === 'running') {
      return { ...base, model, tone: 'busy', line: withModel(variant ? '重翻中' : '翻译中', model, variant ? '翻完前只读' : null),
        actions: [{ kind: 'open-run', label: '看对话' }], readOnly: Boolean(variant) };
    }
    if (own.status === 'error') {
      return { ...base, model, tone: 'error', line: [`出错了：${own.error ?? '未知错误'}`], actions: [{ kind: 'open-run', label: '看对话' }], readOnly: false };
    }
    if (importProblem?.runId === own.id) {
      return { ...base, model, tone: 'error', line: [`没导入：${importProblem.message}`], readOnly: false,
        actions: [{ kind: 'open-run', label: '看对话' }, ...(importProblem.alignment ? [{ kind: 'force-import' as const, label: '仍然导入' }] : [])] };
    }
    // 一轮结束、还没导入也没报错：自动导入正在进行
    return { ...base, model, tone: 'busy', line: ['正在导入'], actions: [], readOnly: Boolean(variant) };
  }
  const model = variant?.import?.model ?? null;
  if (needsLogin) {
    return { ...base, model, tone: 'wait', line: ['要先登录一次 Agent 页才能看进度'], actions: [{ kind: 'login', label: '去登录' }], readOnly: false };
  }
  const filled = countFilled(data.rows, text);
  const status = filled.total && filled.done < filled.total ? `已导入 ${filled.done}/${filled.total} 段` : '已完成';
  return { ...base, model, tone: 'done', line: model ? [status, model] : [status], actions: [], readOnly: false };
}

/** 没登录 Agent 页时不知道是哪个 Agent 在跑：放一个占位版本，状态行提示去登录 */
function loginPlaceholder(projectId: string): VersionView {
  return {
    id: `${projectId}--agent`, source: 'agent', harness: null, name: 'Agent', model: null, tone: 'wait',
    line: ['要先登录一次 Agent 页才能看进度'], actions: [{ kind: 'login', label: '去登录' }],
    readOnly: true, translate: 'none', pending: true, variant: null, text: () => null,
  };
}

export function buildVersions(input: VersionsInput): { versions: VersionView[]; addable: Harness[] } {
  const { data, run, needsLogin } = input;
  const versions: VersionView[] = [webVersion(data)];
  for (const harness of AGENT_ORDER) {
    const variant = data.variants.find(item => variantHarness(item) === harness) ?? null;
    if (variant || (run && runHarness(run) === harness)) versions.push(agentVersion(input, harness, variant));
  }
  if (needsLogin && !versions.some(version => version.source === 'agent')) versions.push(loginPlaceholder(data.project.id));
  for (const variant of data.variants.filter(item => item.kind === 'model')) versions.push(modelVersion(variant, data.rows));
  const addable = AGENT_ORDER.filter(harness => !versions.some(version => version.harness === harness));
  return { versions, addable };
}

/** 主译本：后端给的那一版；找不到（或还没有译文）就用网页版 */
export function pickPrimary(versions: VersionView[], primaryId: string | undefined): VersionView {
  return versions.find(version => version.id === primaryId && !version.pending) ?? versions[0];
}

/** 对照栏默认显示：正在跑的那个 Agent → 最近导入的 → 第一个 */
export function defaultCompare(versions: VersionView[], primary: VersionView, run?: RunMeta): VersionView | null {
  const others = versions.filter(version => version.id !== primary.id);
  if (run) {
    const live = others.find(version => version.harness === runHarness(run) && version.tone !== 'done');
    if (live) return live;
  }
  const byImport = others.filter(version => version.variant?.import)
    .sort((a, b) => b.variant!.import!.imported_at.localeCompare(a.variant!.import!.imported_at));
  return byImport[0] ?? others[0] ?? null;
}
