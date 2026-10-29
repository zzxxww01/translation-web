# 文章工作台前端重做 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把文章工作台重做成「英文 | 主译本 | 对照」三栏、视觉方向 A「书页」：状态只写在栏头状态行，Agent 版能「重新翻译（只换模型）」，「＋」加新 Agent 版时选 Agent 和模型，网页版没翻完才有「继续翻译」，对照栏一键「设为主译本」；导入页改成两个勾选。

**Architecture:** 所有「这一版是什么、什么状态、能做什么」的判断集中在纯函数模块 `lib/versions.ts`（有单测），组件只负责显示。弹框、模型列表、Agent 卡片、状态行、栏头都是独立的小组件。`PaneGrid` 保持 10-27 的连续阅读（三栏各自滚动，不强求等高），只加主译本底色、只读、收起竖条状态点和纸张外观。

**Tech Stack:** React 19、TypeScript、Tailwind v4、TanStack Query 5、Radix（Popover、RadioGroup、DropdownMenu）、lucide-react、vitest + jsdom、Playwright。

设计文档：`docs/superpowers/specs/2026-10-28-workbench-agent-model-design.md`。**先完成** `2026-10-28-workbench-backend-support.md`（主译本接口、导入的 `model`/`force`/409、Gemini 改名都在那里）。

所有前端命令都在 `C:/Users/DELL/AppData/Local/Temp/ta-workbench-agent-model/web/frontend` 下执行。

---

## 文件

| 文件 | 职责 |
|---|---|
| `src/main.tsx`、`src/styles/fluid-theme.css`、`package.json` | 思源宋体 400、Source Serif 4、`--font-source` |
| `src/features/articles/types.ts`、`api.ts` | 主译本字段、`setPrimary`、导入带 `model`/`force` |
| `src/features/articles/lib/claude.ts` | `startClaudeTrack(projectId, choice, title)`、`importClaudeTrack(projectId, run, force)`、`AlignmentTooLow` |
| `src/features/articles/lib/agentChoice.ts`（新） | Agent + 模型的选择与记忆；取代 `lib/agentOptions.ts` |
| `src/features/articles/lib/versions.ts`（新） | 各版本的视图模型：名字、模型、状态行、行动、只读、翻译按钮、主译本、对照默认 |
| `src/features/articles/lib/panes.ts`、`lib/rows.ts` | 栏 id 改 `main/compare`（旧键迁移）；中英文排版 |
| `src/features/articles/components/EditableText.tsx` | `readOnly` |
| `src/features/articles/components/StatusLine.tsx`（新） | 状态行 + 圆点色板 `TONE_DOT` |
| `src/features/articles/components/VersionHeader.tsx`（新） | 三行栏头、`IconAction` |
| `src/features/articles/components/ColumnMenu.tsx`（新） | 栏头「⋯」（Popover） |
| `src/features/articles/components/SaveStatus.tsx`（新） | 顶栏保存状态 / 保存按钮 |
| `src/features/articles/components/ModelList.tsx`（新） | 模型单选列表 |
| `src/features/articles/components/AgentCards.tsx`（新） | Agent 卡片、`AgentChoiceFields` |
| `src/features/articles/components/TranslatePopovers.tsx`（新） | `RetranslatePopover`、`AddAgentPopover` |
| `src/features/articles/components/VersionTabs.tsx`（新） | 对照栏分段标签 / 窄屏下拉 |
| `src/features/articles/components/CompareEmpty.tsx`（新） | 对照栏没有别的版本时的就地表单 |
| `src/features/articles/components/WorkbenchTopBar.tsx`（新） | 顶栏 |
| `src/features/articles/components/PaneGrid.tsx` | 纸张外观、主译本底色、只读、状态点、`versionKey`、`empty` |
| `src/features/articles/components/Workbench.tsx` | 重写：取数据、组装栏、行动回调 |
| `src/features/articles/components/ArticlePreview.tsx`、`lib/importFlow.ts` | 导入页两个勾选 |
| 删除 | `components/ArticleAgentChoice.tsx`、`lib/agentOptions.ts` |
| 测试 | `lib/versions.test.ts`、`lib/agentChoice.test.ts`（新）；`lib/lib.test.ts`、`articles.test.tsx`、`tests/e2e/article-reading.spec.ts` |

---

### Task 0: 准备依赖

- [ ] **Step 1:** `npm ci`（worktree 里还没有 node_modules）
- [ ] **Step 2:** `npm test` → 记下基线（应全部通过）

---

### Task 1: 字体

**Files:** `package.json`、`src/main.tsx`、`src/styles/fluid-theme.css`

- [ ] **Step 1: 装英文衬线体**

Run: `npm install @fontsource-variable/source-serif-4@^5.2.0`
然后 `npm audit --omit=dev` → 0 vulnerabilities（CI 要求零漏洞；有新 advisory 时停下来报告，不要升级无关包）。

- [ ] **Step 2: 引入**

`src/main.tsx` 在 `import '@fontsource/noto-serif-sc/600.css'` 上面加：

```ts
import '@fontsource/noto-serif-sc/400.css' // 工作台中文正文用宋体
import '@fontsource-variable/source-serif-4/wght.css' // 工作台英文原文
```

`src/styles/fluid-theme.css` 在 `--font-display: …;` 下面加：

```css
    --font-source: "Source Serif 4 Variable", "Source Serif 4", Georgia, "Times New Roman", serif;
```

- [ ] **Step 3:** `npx tsc -b && npm run build` → 成功
- [ ] **Step 4: 提交**

```bash
git add package.json package-lock.json src/main.tsx src/styles/fluid-theme.css
git commit -m "feat(workbench): self-host serif faces for reading columns"
```

---

### Task 2: 类型、接口、Agent 任务的启动与导入

**Files:** `src/features/articles/types.ts`、`src/features/articles/api.ts`、`src/features/articles/lib/claude.ts`

- [ ] **Step 1: 改 `types.ts`**

文件顶部加 `import type { Harness } from '@/features/skills/harness';`

`WorkbenchProject` 在 `claude_run_id` 下面加：

```ts
  /** 用户选的主译本（主项目或孪生项目 id）；null = 没选过 */
  primary_target?: string | null;
  /** 实际的主译本：选过的那个，或后端按默认规则算出的（services/article_primary.py） */
  primary?: string;
```

`ClaudeImportRecord` 在 `run_id` 下面加：

```ts
  /** 跑这一版的 Agent；旧记录没有，用 label 反推 */
  agent?: Harness;
  model?: string | null;
```

`PaneId` 改为：

```ts
export type PaneId = 'source' | 'main' | 'compare';
```

- [ ] **Step 2: 改 `api.ts`**

`articlesApi` 里加：

```ts
  setPrimary: (projectId: string, target: string) =>
    apiClient.put<{ ok: boolean; primary_target: string }>(
      `/projects/${projectId}/workbench/primary`, { target }, { retry: false }),
```

`importClaude` 的 body 类型改为：

```ts
  importClaude: (projectId: string, body: {
    run_id: string; zh_markdown: string; en_markdown: string; agent: Harness; model?: string | null; force?: boolean;
  }) =>
```

- [ ] **Step 3: 改 `lib/claude.ts`**

import 区加 `import { ApiErrorWrapper } from '@/shared/api/client';` 和 `import type { AgentChoice } from './agentChoice';`，去掉不再用的 `Harness` import。

`NoClaudeOutput` 的文案缩短（它会进状态行「没导入：…」）：

```ts
export class NoClaudeOutput extends Error {
  constructor() {
    super('没找到同一目录下的 zh.md 和 en.md');
    this.name = 'NoClaudeOutput';
  }
}

/** 后端 409：Agent 的英文稿和下载的原文对不上（多半不是这篇），可以「仍然导入」。 */
export class AlignmentTooLow extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AlignmentTooLow';
  }
}
```

`startClaudeTrack` 和 `importClaudeTrack` 换成：

```ts
/** 把下载好的原文 HTML 交给所选 Agent 跑 four-step-translate，并记下这篇文章对应的对话。 */
export async function startClaudeTrack(projectId: string, choice: AgentChoice, title?: string): Promise<RunMeta> {
  const html = await articlesApi.sourceHtml(projectId);
  const model = choice.model.trim();
  const run = await startRun({
    skill: CLAUDE_SKILL, message: CLAUDE_MESSAGE, files: [html], harness: choice.harness,
    ...(model ? { model } : {}), autoReplyMinutes: AUTO_REPLY_MINUTES, title,
  });
  await articlesApi.setClaudeRun(projectId, run.id);
  return run;
}

/** 从任务取回 zh.md / en.md，对齐后存成该 Agent 对应的那一版；记下 Agent 和实际模型。 */
export async function importClaudeTrack(projectId: string, run: RunMeta, force = false) {
  const outputs = findClaudeOutputs(await skillsApi.files(run.id));
  if (!outputs) throw new NoClaudeOutput();
  const [zh, en] = await Promise.all([readText(run.id, outputs.zh), readText(run.id, outputs.en)]);
  try {
    return await articlesApi.importClaude(projectId, {
      run_id: run.id, zh_markdown: zh, en_markdown: en, agent: run.harness ?? 'claude',
      model: run.actual_model ?? run.model ?? null, force,
    });
  } catch (error) {
    if (error instanceof ApiErrorWrapper && error.status === 409) throw new AlignmentTooLow(error.message);
    throw error;
  }
}
```

- [ ] **Step 4:** 先不跑类型检查（`agentChoice.ts` 在 Task 3 建）。直接进 Task 3，两个 Task 一起提交。

---

### Task 3: Agent 选择与记忆

**Files:**
- Create: `src/features/articles/lib/agentChoice.ts`
- Create: `src/features/articles/lib/agentChoice.test.ts`
- Delete: `src/features/articles/lib/agentOptions.ts`

- [ ] **Step 1: 写失败的测试** `agentChoice.test.ts`：

```ts
// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest';
import { loadModel } from '@/features/skills/models';
import { loadHarness } from '@/features/skills/harness';
import { ARTICLE_HARNESSES, loadAgentChoice, rememberedModel, saveAgentChoice } from './agentChoice';

describe('agentChoice', () => {
  beforeEach(() => localStorage.clear());

  it('lists Codex first and defaults to it', () => {
    expect(ARTICLE_HARNESSES.map(item => item.id)).toEqual(['codex', 'claude', 'antigravity']);
    expect(loadAgentChoice()).toEqual({ harness: 'codex', model: '' });
  });

  it('remembers the model per agent in the same place as the Agent page', () => {
    saveAgentChoice({ harness: 'claude', model: ' opus ' });
    saveAgentChoice({ harness: 'codex', model: 'gpt-5.5-codex' });
    expect(loadHarness('four-step-translate', 'claude')).toBe('codex');
    expect(loadModel('four-step-translate', 'claude')).toBe('opus');
    expect(rememberedModel('codex')).toBe('gpt-5.5-codex');
    expect(loadAgentChoice()).toEqual({ harness: 'codex', model: 'gpt-5.5-codex' });
    expect(loadAgentChoice('claude')).toEqual({ harness: 'claude', model: 'opus' });
  });

  it('only picks from the allowed agents', () => {
    saveAgentChoice({ harness: 'codex', model: '' });
    expect(loadAgentChoice(undefined, ['claude', 'antigravity']).harness).toBe('claude');
    expect(loadAgentChoice('codex', ['antigravity']).harness).toBe('antigravity');
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `npx vitest run src/features/articles/lib/agentChoice.test.ts`
Expected: FAIL，找不到 `./agentChoice`

- [ ] **Step 3: 实现** `agentChoice.ts`：

```ts
import { HARNESSES, loadHarness, saveHarness, type Harness } from '@/features/skills/harness';
import { loadModel, saveModel } from '@/features/skills/models';
import { CLAUDE_SKILL } from './claude';

/** 文章里交给 Agent 时的选择；model 为空串 = 用这个 Agent 的默认模型 */
export interface AgentChoice {
  harness: Harness;
  model: string;
}

export const DEFAULT_HARNESS: Harness = 'codex';

/** 文章入口里 Agent 的排列：默认的 Codex 在前，其余照 Agent 页的顺序 */
export const ARTICLE_HARNESSES = [...HARNESSES].sort(
  (a, b) => Number(b.id === DEFAULT_HARNESS) - Number(a.id === DEFAULT_HARNESS),
);

/** 这个 Agent 上次在翻译 Agent（four-step-translate）里用的模型，和 Agent 页共用一份记忆 */
export function rememberedModel(harness: Harness): string {
  return loadModel(CLAUDE_SKILL, harness);
}

/** 打开选择框时默认选谁：指定的 → 上次用的 → Codex → 可选里的第一个；模型取它上次用的 */
export function loadAgentChoice(preferred?: Harness, allowed: Harness[] = ARTICLE_HARNESSES.map(item => item.id)): AgentChoice {
  const saved = loadHarness(CLAUDE_SKILL, DEFAULT_HARNESS);
  const harness = [preferred, saved, DEFAULT_HARNESS, ...allowed].find(
    (id): id is Harness => Boolean(id) && allowed.includes(id as Harness),
  ) ?? allowed[0] ?? DEFAULT_HARNESS;
  return { harness, model: rememberedModel(harness) };
}

/** 真正开始翻译时才记下来 */
export function saveAgentChoice(choice: AgentChoice): void {
  saveHarness(CLAUDE_SKILL, choice.harness);
  saveModel(CLAUDE_SKILL, choice.harness, choice.model.trim());
}
```

删除 `lib/agentOptions.ts`（`ArticleAgentChoice.tsx` 和 `ArticlePreview.tsx` 还在引用它，Task 13 一并处理；在那之前把这两个文件里的 import 改成从 `../lib/agentChoice` 引 `ARTICLE_HARNESSES`，保证能编译）。

- [ ] **Step 4: 跑测试**

Run: `npx vitest run src/features/articles/lib/agentChoice.test.ts`
Expected: 3 passed

- [ ] **Step 5: 提交**（Workbench 和 importFlow 还按旧签名调用 `startClaudeTrack`，`tsc` 会报错；这两处在 Task 12、13 重写。本次只提交，不跑全量类型检查）

```bash
git add src/features/articles/types.ts src/features/articles/api.ts src/features/articles/lib/claude.ts src/features/articles/lib/agentChoice.ts src/features/articles/lib/agentChoice.test.ts src/features/articles/components/ArticleAgentChoice.tsx src/features/articles/components/ArticlePreview.tsx
git rm src/features/articles/lib/agentOptions.ts
git commit -m "feat(workbench): agent + model choice with shared memory; import carries model"
```

---

### Task 4: 版本视图模型 `lib/versions.ts`

**Files:**
- Create: `src/features/articles/lib/versions.ts`
- Create: `src/features/articles/lib/versions.test.ts`

- [ ] **Step 1: 写失败的测试** `versions.test.ts`：

```ts
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
    expect(build(failed).versions[0]).toMatchObject({ tone: 'error', line: ['出错了：额度用完'], translate: 'continue' });
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
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `npx vitest run src/features/articles/lib/versions.test.ts`
Expected: FAIL，找不到 `./versions`

- [ ] **Step 3: 实现** `versions.ts`：

```ts
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
```

- [ ] **Step 4: 跑测试**

Run: `npx vitest run src/features/articles/lib/versions.test.ts`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/features/articles/lib/versions.ts src/features/articles/lib/versions.test.ts
git commit -m "feat(workbench): one view model for every translation version"
```

---

### Task 5: 栏 id、排版

**Files:** `src/features/articles/lib/panes.ts`、`src/features/articles/lib/rows.ts`、`src/features/articles/lib/lib.test.ts`

- [ ] **Step 1: 改测试** `lib.test.ts` 的 `describe('panes')` 换成：

```ts
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
```

文件第一行加 `// @vitest-environment jsdom`，import 加 `loadCollapsed`。

- [ ] **Step 2: 跑测试，确认失败**

Run: `npx vitest run src/features/articles/lib/lib.test.ts`
Expected: FAIL

- [ ] **Step 3: 实现**

`panes.ts`：

```ts
export const PANES: PaneId[] = ['source', 'main', 'compare'];
```

```ts
export const NONE_COLLAPSED: Collapsed = { source: false, main: false, compare: false };
```

`loadCollapsed` 换成：

```ts
export function loadCollapsed(): Collapsed {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as Record<string, boolean> | null;
    if (!raw) return NONE_COLLAPSED;
    // 10-28 之前存的是 web / alt
    const value: Collapsed = { source: Boolean(raw.source), main: Boolean(raw.main ?? raw.web), compare: Boolean(raw.compare ?? raw.alt) };
    return PANES.every(id => value[id]) ? NONE_COLLAPSED : value;
  } catch {
    return NONE_COLLAPSED;
  }
}
```

`rows.ts` 换成：

```ts
import type { WorkbenchRow } from '../types';

/** 行的版式。英文原文用衬线体（Source Serif），中文用思源宋体；章节标题、列表、引用、代码各有样式。 */
export function rowTextClass(row: WorkbenchRow, lang: 'en' | 'zh' = 'zh'): string {
  const face = lang === 'en' ? '[font-family:var(--font-source)]' : '[font-family:var(--font-display)]';
  if (row.kind === 'section') return `pt-6 text-[19px] font-semibold leading-snug text-text-primary ${face}`;
  if (/^h[1-4]$/.test(row.kind)) return `pt-3 text-[16.5px] font-semibold leading-snug text-text-primary ${face}`;
  if (row.is_metadata) return 'text-[13px] leading-relaxed text-text-muted';
  if (row.kind === 'blockquote') return `border-l-2 border-border pl-3 text-[15px] leading-[1.85] text-text-secondary ${face}`;
  if (row.kind === 'code' || row.kind === 'table') return 'whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed text-text-secondary';
  return lang === 'en'
    ? `text-[14.5px] leading-[1.78] text-[#5d5560] ${face}`
    : `text-[15.5px] leading-[1.95] text-text-primary ${face}`;
}
```

- [ ] **Step 4:** `npx vitest run src/features/articles/lib/lib.test.ts` → 通过
- [ ] **Step 5: 提交**

```bash
git add src/features/articles/lib/panes.ts src/features/articles/lib/rows.ts src/features/articles/lib/lib.test.ts
git commit -m "feat(workbench): main/compare panes and serif reading type"
```

---

### Task 6: EditableText 只读

**Files:** `src/features/articles/components/EditableText.tsx`、`src/features/articles/articles.test.tsx`

- [ ] **Step 1: 写失败的测试**（加到 `describe('EditableText display')` 里）

```tsx
  it('shows read-only text without an edit affordance and ignores adoption', async () => {
    const onSave = vi.fn();
    const ref = { current: null as import('./components/EditableText').EditableTextHandle | null };
    await render(<EditableText ref={ref} id="main:s/p" value="旧译文" placeholder="" ariaLabel="主译本：S" onSave={onSave} readOnly />);
    expect(host.textContent).toBe('旧译文');
    expect(host.querySelector('[role="button"]')).toBeNull();
    await act(async () => { await ref.current!.adopt('新的'); });
    expect(onSave).not.toHaveBeenCalled();
    expect(host.textContent).toBe('旧译文');
  });
```

- [ ] **Step 2:** `npx vitest run src/features/articles/articles.test.tsx -t "read-only"` → FAIL（`readOnly` 不存在）

- [ ] **Step 3: 实现**

`EditableTextProps` 加 `readOnly?: boolean;`，函数参数加 `readOnly = false`。

`useImperativeHandle` 里 `adopt` 的第一行改成：

```ts
      if (protectedDraft || readOnly) return;
```

依赖数组改成 `[protectedDraft, readOnly, save]`。

在 `const Container = inline ? 'span' : 'div';` 后面、`return (` 前面加：

```tsx
  // 重翻期间这一版只读：翻完会整篇替换，期间改了也留不住
  if (readOnly) {
    return (
      <Container className={cn('group/edit relative', className)}>
        <Container className={cn(inline ? 'rounded' : BOX, 'whitespace-pre-wrap border-transparent text-text-secondary/80')}>
          {text ? <InlineMarkdown text={text} /> : <span className="text-text-disabled">{placeholder}</span>}
        </Container>
      </Container>
    );
  }
```

- [ ] **Step 4:** `npx vitest run src/features/articles/articles.test.tsx -t "EditableText"` → 通过
- [ ] **Step 5: 提交**

```bash
git add src/features/articles/components/EditableText.tsx src/features/articles/articles.test.tsx
git commit -m "feat(workbench): read-only paragraphs while a version is re-translated"
```

---

### Task 7: 栏头积木：状态行、栏头、⋯ 菜单、保存状态

**Files:**
- Create: `src/features/articles/components/StatusLine.tsx`
- Create: `src/features/articles/components/VersionHeader.tsx`
- Create: `src/features/articles/components/ColumnMenu.tsx`
- Create: `src/features/articles/components/SaveStatus.tsx`

这几个是纯显示组件，行为由 Task 12 的工作台测试覆盖。

- [ ] **Step 1: `StatusLine.tsx`**

```tsx
import { Fragment } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Tone, VersionAction, VersionView } from '../lib/versions';

export const TONE_DOT: Record<Tone, string> = {
  done: 'bg-success',
  busy: 'bg-info shadow-[0_0_0_3px_var(--color-info-light)]',
  wait: 'bg-warning',
  error: 'bg-error',
  idle: 'bg-border',
};

const TONE_TEXT: Record<Tone, string> = {
  done: 'text-text-muted', busy: 'text-text-muted', idle: 'text-text-muted', wait: 'text-[#94600f]', error: 'text-error',
};

const LEADS_SOMEWHERE = new Set<VersionAction['kind']>(['confirm-terms', 'open-run', 'login']);

/** 版本名下面那一行：「● 状态 · 模型 · 补充 · 行动」。所有状态都写在这里，不另外弹提示。 */
export function StatusLine({ version, onAction }: { version: VersionView; onAction: (action: VersionAction) => void }) {
  const text = version.line.join(' · ');
  return (
    <p className={cn('mt-1.5 flex min-w-0 items-center gap-1.5 text-[12px] leading-5', TONE_TEXT[version.tone])} title={text}>
      <span aria-hidden className={cn('h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[version.tone])} />
      <span className="min-w-0 truncate">{text}</span>
      {version.actions.map(action => (
        <Fragment key={action.label}>
          <span aria-hidden className="text-text-disabled">·</span>
          <button type="button" onClick={() => onAction(action)}
            className="inline-flex shrink-0 items-center gap-0.5 text-primary-700 underline-offset-2 hover:underline">
            {action.label}
            {LEADS_SOMEWHERE.has(action.kind) && <ArrowRight className="h-3 w-3" />}
          </button>
        </Fragment>
      ))}
    </p>
  );
}
```

- [ ] **Step 2: `VersionHeader.tsx`**

```tsx
import type { ComponentProps, ReactNode } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

/** 栏头的三行排版块：小标题、版本名（或对照栏的标签）、状态行；右上角放操作。 */
export function VersionHeader({ eyebrow, primary = false, title, line, actions }: {
  eyebrow: string;
  primary?: boolean;
  title: ReactNode;
  line: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start gap-2">
      <div className="min-w-0 flex-1">
        <div className={cn('mb-1.5 flex items-center gap-1 text-[11px] tracking-[0.14em]', primary ? 'text-primary-500' : 'text-text-muted/70')}>
          {primary && <Star className="h-3 w-3 fill-current" />}
          {eyebrow}
        </div>
        <div className="flex min-h-[26px] items-center">{title}</div>
        {line}
      </div>
      {actions && <div className="-mr-1 -mt-1 flex shrink-0 items-center gap-0.5">{actions}</div>}
    </div>
  );
}

/** 版本名：宋体 16px */
export function VersionName({ children, english = false }: { children: ReactNode; english?: boolean }) {
  return (
    <span className={cn('truncate text-[16px] font-semibold leading-snug text-text-primary',
      english ? '[font-family:var(--font-source)]' : '[font-family:var(--font-display)]')}>
      {children}
    </span>
  );
}

export const ICON_BUTTON = 'inline-flex h-8 w-8 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-[rgba(43,39,48,0.05)] hover:text-text-primary disabled:opacity-40';

/** 只有图标的按钮；能被 Radix 的 asChild 包（ref 和其余属性都传下去） */
export function IconAction({ label, className, children, ...props }: ComponentProps<'button'> & { label: string }) {
  return (
    <button type="button" aria-label={label} title={label} className={cn(ICON_BUTTON, className)} {...props}>
      {children}
    </button>
  );
}
```

- [ ] **Step 3: `ColumnMenu.tsx`**（用 Popover：点击打开，jsdom 里也能测）

```tsx
import { useState } from 'react';
import { MoreHorizontal } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { IconAction } from './VersionHeader';

export interface MenuItem {
  label: string;
  onSelect: () => void;
}

/** 栏头的「⋯」：这一栏自己的操作 */
export function ColumnMenu({ label, items }: { label: string; items: MenuItem[] }) {
  const [open, setOpen] = useState(false);
  if (!items.length) return null;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <IconAction label={label}><MoreHorizontal className="h-4 w-4" /></IconAction>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-48 rounded-xl border-border-subtle p-1.5 shadow-[0_12px_32px_rgba(43,39,48,0.14)]">
        {items.map(item => (
          <button key={item.label} type="button" onClick={() => { setOpen(false); item.onSelect(); }}
            className="block w-full rounded-md px-2.5 py-1.5 text-left text-[13px] text-text-secondary hover:bg-bg-hover hover:text-text-primary">
            {item.label}
          </button>
        ))}
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 4: `SaveStatus.tsx`**

```tsx
import { AlertCircle, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePaneSaveState } from '../lib/edits';

const clock = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });

/** 顶栏的保存状态，同时也是保存按钮（Ctrl/⌘+S 一样）：两个中文栏合并显示 */
export function SaveStatus({ saving, onSave }: { saving: boolean; onSave: () => void }) {
  const main = usePaneSaveState('main');
  const compare = usePaneSaveState('compare');
  const failed = main.failed + compare.failed;
  const busy = saving || main.busy + compare.busy > 0;
  const savedAt = Math.max(main.savedAt ?? 0, compare.savedAt ?? 0) || null;
  const text = failed ? `${failed} 段没保存上` : busy ? '保存中…' : savedAt ? `已保存 ${clock.format(savedAt)}` : '保存';
  return (
    <button type="button" aria-label="保存" title="Ctrl/⌘ + S：立刻保存（改动本来就会自动保存）" disabled={saving} onClick={onSave}
      className={cn('inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-[12.5px] transition-colors hover:bg-[rgba(43,39,48,0.05)]',
        failed ? 'text-error' : 'text-text-muted')}>
      {failed ? <AlertCircle className="h-3.5 w-3.5" /> : <Check className={cn('h-3.5 w-3.5', savedAt && 'text-success')} />}
      {text}
    </button>
  );
}
```

- [ ] **Step 5:** `npx eslint src/features/articles/components` → 无错误
- [ ] **Step 6: 提交**

```bash
git add src/features/articles/components/StatusLine.tsx src/features/articles/components/VersionHeader.tsx src/features/articles/components/ColumnMenu.tsx src/features/articles/components/SaveStatus.tsx
git commit -m "feat(workbench): status line, header block, column menu and save status"
```

---

### Task 8: 模型列表、Agent 卡片

**Files:**
- Create: `src/features/articles/components/ModelList.tsx`
- Create: `src/features/articles/components/AgentCards.tsx`

- [ ] **Step 1: `ModelList.tsx`**

```tsx
import { useState } from 'react';
import * as RadioGroup from '@radix-ui/react-radio-group';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { skillsApi } from '@/features/skills/api';
import type { Harness } from '@/features/skills/harness';
import { cn } from '@/lib/utils';

const DEFAULT = '__default__';
const CUSTOM = '__custom__';

/** 模型单选列表：默认（写明是哪个）/ 服务器清单 / 填写模型 ID。value 为空串 = 默认。 */
export function ModelList({ harness, value, onChange, lastUsed = '', disabled = false }: {
  harness: Harness;
  value: string;
  onChange: (model: string) => void;
  lastUsed?: string;
  disabled?: boolean;
}) {
  const client = useQueryClient();
  const key = ['skills', 'models', harness];
  const query = useQuery({ queryKey: key, queryFn: () => skillsApi.models(harness), staleTime: 60_000, retry: false });
  const refresh = useMutation({
    mutationFn: () => skillsApi.models(harness, true),
    onSuccess: data => client.setQueryData(key, data),
  });
  const models = query.data?.models ?? [];
  const [custom, setCustom] = useState(false);
  const unknown = Boolean(value) && !query.isPending && !models.some(model => model.id === value);
  const isCustom = custom || unknown;
  const selected = isCustom ? CUSTOM : value || DEFAULT;
  const fetching = query.isFetching || refresh.isPending;
  const note = query.error || refresh.error
    ? '模型清单读取失败，仍可使用默认模型或填写模型 ID'
    : query.data?.warning ?? (lastUsed ? `上次用 ${lastUsed}` : '');

  return (
    <div>
      <RadioGroup.Root aria-label="模型" value={selected} disabled={disabled}
        onValueChange={next => {
          setCustom(next === CUSTOM);
          onChange(next === CUSTOM || next === DEFAULT ? '' : next);
        }}
        className="max-h-[236px] overflow-y-auto rounded-[10px] border border-border-subtle bg-white">
        <Option value={DEFAULT} name="默认" tag={query.data?.default_model ?? '账号默认'} />
        {models.map(model => (
          <Option key={model.id} value={model.id} name={model.label} tag={model.id === lastUsed ? '上次用' : undefined} />
        ))}
        <Option value={CUSTOM} name="填写模型 ID…" dashed />
      </RadioGroup.Root>
      {isCustom && (
        <input aria-label="模型 ID" value={value} maxLength={128} disabled={disabled} autoFocus
          onChange={event => onChange(event.target.value)}
          placeholder={harness === 'claude' ? '例如 opus 或完整模型 ID' : '填写完整模型 ID'}
          className="mt-2 w-full rounded-lg border border-border bg-white px-2.5 py-1.5 text-[13px] text-text-primary focus:border-primary-300 focus:outline-none" />
      )}
      <p className="mt-2 flex items-center gap-2 text-[11.5px] text-text-muted">
        <span className="min-w-0 flex-1 truncate">{note}</span>
        <button type="button" disabled={disabled || fetching} onClick={() => refresh.mutate()}
          className="shrink-0 text-primary-700 disabled:opacity-50">
          {fetching ? '读取中…' : '刷新清单'}
        </button>
      </p>
    </div>
  );
}

function Option({ value, name, tag, dashed = false }: { value: string; name: string; tag?: string; dashed?: boolean }) {
  return (
    <RadioGroup.Item value={value}
      className="group flex w-full items-center gap-2.5 border-t border-border-subtle px-3 py-2 text-left text-[13px] first:border-t-0 focus-visible:bg-primary-50/70 focus-visible:outline-none disabled:opacity-50 data-[state=checked]:bg-primary-50">
      <span aria-hidden className={cn('h-[15px] w-[15px] shrink-0 rounded-full border-[1.5px] border-border bg-white transition-[border-width] group-data-[state=checked]:border-[4.5px] group-data-[state=checked]:border-primary-500', dashed && 'border-dashed')} />
      <span className={cn('min-w-0 flex-1 truncate', dashed ? 'text-text-muted' : 'text-text-primary')}>{name}</span>
      {tag && <span className="shrink-0 text-[11px] text-text-muted group-data-[state=checked]:text-primary-700">{tag}</span>}
    </RadioGroup.Item>
  );
}
```

- [ ] **Step 2: `AgentCards.tsx`**

```tsx
import * as RadioGroup from '@radix-ui/react-radio-group';
import { Gem, Sparkles, SquareTerminal, type LucideIcon } from 'lucide-react';
import { HARNESSES, type Harness } from '@/features/skills/harness';
import { rememberedModel, type AgentChoice } from '../lib/agentChoice';
import { ModelList } from './ModelList';

const LOOK: Record<Harness, { icon: LucideIcon; color: string }> = {
  codex: { icon: SquareTerminal, color: '#2b2730' },
  claude: { icon: Sparkles, color: '#c56f98' },
  antigravity: { icon: Gem, color: '#4f6d9a' },
};

/** Agent 单选卡片：图标方块 + 名字 + 一句说明 */
export function AgentCards({ options, value, onChange, disabled = false }: {
  options: Harness[];
  value: Harness;
  onChange: (harness: Harness) => void;
  disabled?: boolean;
}) {
  return (
    <RadioGroup.Root aria-label="Agent" value={value} disabled={disabled} onValueChange={next => onChange(next as Harness)}
      className="grid grid-cols-[repeat(auto-fit,minmax(132px,1fr))] gap-2">
      {options.map(id => {
        const item = HARNESSES.find(harness => harness.id === id)!;
        const { icon: Icon, color } = LOOK[id];
        return (
          <RadioGroup.Item key={id} value={id}
            className="flex min-w-0 items-center gap-2.5 rounded-xl border border-border-subtle bg-white px-3 py-2.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-200 disabled:opacity-50 data-[state=checked]:border-primary-300 data-[state=checked]:bg-primary-50 data-[state=checked]:shadow-[0_0_0_3px_rgba(163,61,112,0.08)]">
            <span aria-hidden className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white" style={{ background: color }}>
              <Icon className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-[13px] font-semibold text-text-primary">{item.label}</span>
              <span className="block truncate text-[11px] text-text-muted" title={item.note}>{item.note}</span>
            </span>
          </RadioGroup.Item>
        );
      })}
    </RadioGroup.Root>
  );
}

/** Agent 卡片 + 模型列表；换 Agent 时模型换成它上次用的 */
export function AgentChoiceFields({ options, value, onChange, disabled = false }: {
  options: Harness[];
  value: AgentChoice;
  onChange: (choice: AgentChoice) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <AgentCards options={options} value={value.harness} disabled={disabled}
        onChange={harness => onChange({ harness, model: rememberedModel(harness) })} />
      <div className="mb-1.5 mt-3.5 text-[11px] tracking-[0.12em] text-text-muted">模型</div>
      <ModelList key={value.harness} harness={value.harness} value={value.model} lastUsed={rememberedModel(value.harness)}
        disabled={disabled} onChange={model => onChange({ ...value, model })} />
    </div>
  );
}
```

- [ ] **Step 3:** `npx tsc -b --noEmit 2>&1 | grep -E "ModelList|AgentCards"` → 没有这两个文件的错误
- [ ] **Step 4: 提交**

```bash
git add src/features/articles/components/ModelList.tsx src/features/articles/components/AgentCards.tsx
git commit -m "feat(workbench): model list and agent cards"
```

---

### Task 9: 两种弹框

**Files:** Create `src/features/articles/components/TranslatePopovers.tsx`

- [ ] **Step 1: 实现**

```tsx
import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { Harness } from '@/features/skills/harness';
import { articlesApi } from '../api';
import { articleKeys } from '../hooks';
import { loadAgentChoice, rememberedModel, type AgentChoice } from '../lib/agentChoice';
import type { VersionView } from '../lib/versions';
import { AgentChoiceFields } from './AgentCards';
import { ModelList } from './ModelList';

const CONTENT = 'w-[320px] rounded-[14px] border-0 p-[18px] shadow-[0_0_0_1px_rgba(43,39,48,0.06),0_18px_48px_rgba(43,39,48,0.16)]';

function Warning({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3.5 flex gap-2 rounded-[10px] bg-warning-light px-3 py-2.5 text-[12px] leading-relaxed text-[#7a520f]">
      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

function Shell({ title, sub, children, confirmLabel, busy, onCancel, onConfirm }: {
  title: string; sub: string; children: ReactNode; confirmLabel: string; busy: boolean; onCancel: () => void; onConfirm: () => void;
}) {
  return (
    <>
      <h4 className="text-[15.5px] font-semibold text-text-primary [font-family:var(--font-display)]">{title}</h4>
      <p className="mb-3.5 mt-0.5 text-[12px] text-text-muted">{sub}</p>
      {children}
      <div className="mt-4 flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-[34px] rounded-full px-3.5 text-[13px] text-text-secondary hover:bg-bg-hover">取消</button>
        <button type="button" disabled={busy} onClick={onConfirm}
          className="inline-flex h-[34px] items-center gap-1.5 rounded-full bg-primary-500 px-4 text-[13px] font-medium text-white shadow-[0_1px_2px_rgba(116,42,79,0.25),0_4px_12px_rgba(163,61,112,0.18)] hover:bg-primary-600 disabled:opacity-60">
          {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {busy ? '开始中…' : confirmLabel}
        </button>
      </div>
    </>
  );
}

/** Agent 版的「↻ 重新翻译」：Agent 固定，只换模型。onConfirm 成功返回 true 才关框。 */
export function RetranslatePopover({ projectId, version, stopping, busy, onConfirm, children }: {
  projectId: string;
  version: VersionView;
  /** 正在跑、会被先停掉的 Agent 名 */
  stopping: string | null;
  busy: boolean;
  onConfirm: (model: string) => Promise<boolean>;
  children: ReactNode;
}) {
  const harness = version.harness as Harness;
  const [open, setOpen] = useState(false);
  const [model, setModel] = useState('');
  const changes = useQuery({
    queryKey: articleKeys.changes(version.id),
    queryFn: () => articlesApi.changes(projectId, version.id),
    enabled: open && Boolean(version.variant),
    retry: false,
  });
  const edited = changes.data?.changed ?? 0;
  const confirm = async () => {
    if (await onConfirm(model)) setOpen(false);
  };
  return (
    <Popover open={open} onOpenChange={next => { setOpen(next); if (next) setModel(rememberedModel(harness)); }}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="end" className={CONTENT}>
        <Shell title={`重新翻译 ${version.name} 版`} sub="在服务器上跑，关掉页面也不会停" confirmLabel="重新翻译"
          busy={busy} onCancel={() => setOpen(false)} onConfirm={() => void confirm()}>
          <div className="mb-1.5 text-[11px] tracking-[0.12em] text-text-muted">模型</div>
          <ModelList harness={harness} value={model} onChange={setModel} lastUsed={rememberedModel(harness)} disabled={busy} />
          {version.variant && (
            <Warning>
              {`翻完会整篇替换现在的 ${version.name} 版`}
              {edited > 0 ? `，你改过的 ${edited} 段也会被替换` : ''}
              ；翻完前这一版只读。
            </Warning>
          )}
          {stopping && <Warning>{`会先停掉正在跑的 ${stopping}。`}</Warning>}
        </Shell>
      </PopoverContent>
    </Popover>
  );
}

/** 对照栏标签末尾的「＋」：只列还没有译本的 Agent */
export function AddAgentPopover({ options, stopping, busy, onConfirm, children }: {
  options: Harness[];
  stopping: string | null;
  busy: boolean;
  onConfirm: (choice: AgentChoice) => Promise<boolean>;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice(undefined, options));
  const confirm = async () => {
    if (await onConfirm(choice)) setOpen(false);
  };
  return (
    <Popover open={open} onOpenChange={next => { setOpen(next); if (next) setChoice(loadAgentChoice(undefined, options)); }}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="start" className={CONTENT}>
        <Shell title="用 Agent 再翻一版" sub="只列出还没有译本的 Agent" confirmLabel="开始翻译"
          busy={busy} onCancel={() => setOpen(false)} onConfirm={() => void confirm()}>
          <AgentChoiceFields options={options} value={choice} onChange={setChoice} disabled={busy} />
          {stopping && <Warning>{`会先停掉正在跑的 ${stopping}。`}</Warning>}
        </Shell>
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 2:** `npx eslint src/features/articles/components/TranslatePopovers.tsx` → 无错误
- [ ] **Step 3: 提交**

```bash
git add src/features/articles/components/TranslatePopovers.tsx
git commit -m "feat(workbench): retranslate and add-agent popovers"
```

---

### Task 10: 对照栏标签、空状态

**Files:**
- Create: `src/features/articles/components/VersionTabs.tsx`
- Create: `src/features/articles/components/CompareEmpty.tsx`

- [ ] **Step 1: `VersionTabs.tsx`**

```tsx
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import type { VersionView } from '../lib/versions';
import { TONE_DOT } from './StatusLine';

/** 窄于 width 时返回 true（jsdom 没有 ResizeObserver，一律当宽屏） */
function useNarrow(width: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(([entry]) => setNarrow(entry.contentRect.width < width));
    observer.observe(el);
    return () => observer.disconnect();
  }, [width]);
  return [ref, narrow] as const;
}

const dot = (version: VersionView) => version.tone !== 'done' && version.tone !== 'idle'
  ? <span aria-hidden className={cn('h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[version.tone])} /> : null;

/** 对照栏：分段胶囊标签（宽）或下拉（窄、手机）。add 是末尾的「＋」。 */
export function VersionTabs({ versions, value, onChange, add, forceMenu = false }: {
  versions: VersionView[];
  value: string;
  onChange: (id: string) => void;
  add?: ReactNode;
  forceMenu?: boolean;
}) {
  const [ref, narrow] = useNarrow(420);
  const [open, setOpen] = useState(false);
  const current = versions.find(version => version.id === value) ?? versions[0];
  if (forceMenu || narrow) {
    return (
      <div ref={ref} className="flex items-center gap-1">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button type="button" aria-label="切换对照版本"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#f5eff1] px-3 py-1 text-[12.5px] font-medium text-text-primary">
              {dot(current)}{current.name}<ChevronDown className="h-3.5 w-3.5 text-text-muted" />
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-56 rounded-xl p-1.5">
            {versions.map(version => (
              <button key={version.id} type="button" onClick={() => { setOpen(false); onChange(version.id); }}
                className={cn('flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-[13px] hover:bg-bg-hover', version.id === value && 'bg-primary-50')}>
                {dot(version)}<span className="flex-1">{version.name}</span>
                {version.model && <span className="truncate text-[11px] text-text-muted">{version.model}</span>}
              </button>
            ))}
          </PopoverContent>
        </Popover>
        {add}
      </div>
    );
  }
  return (
    <div ref={ref} role="tablist" aria-label="对照版本" className="inline-flex max-w-full items-center gap-0.5 rounded-full bg-[#f5eff1] p-[3px]">
      {versions.map(version => (
        <button key={version.id} type="button" role="tab" aria-selected={version.id === value} onClick={() => onChange(version.id)}
          className={cn('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-[12.5px] transition-colors',
            version.id === value
              ? 'bg-white font-medium text-text-primary shadow-[0_1px_2px_rgba(43,39,48,0.08),0_1px_6px_rgba(43,39,48,0.05)]'
              : 'text-text-muted hover:text-text-primary')}>
          {dot(version)}{version.name}
        </button>
      ))}
      {add}
    </div>
  );
}
```

- [ ] **Step 2: `CompareEmpty.tsx`**

```tsx
import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { Harness } from '@/features/skills/harness';
import { loadAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { AgentChoiceFields } from './AgentCards';

/** 对照栏没有别的版本时：就地选 Agent 和模型开始翻 */
export function CompareEmpty({ options, stopping, busy, onStart }: {
  options: Harness[];
  stopping: string | null;
  busy: boolean;
  onStart: (choice: AgentChoice) => Promise<boolean>;
}) {
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice(undefined, options));
  return (
    <div className="mx-auto max-w-[360px] py-10">
      <h3 className="text-[16px] font-semibold text-text-primary [font-family:var(--font-display)]">选一个 Agent 翻这篇</h3>
      <p className="mb-4 mt-1 text-[12.5px] leading-relaxed text-text-muted">在服务器上跑 four-step-translate，关掉页面也不会停。翻好的译文会出现在这一栏。</p>
      <AgentChoiceFields options={options} value={choice} onChange={setChoice} disabled={busy} />
      {stopping && <p className="mt-3 text-[12px] text-[#7a520f]">会先停掉正在跑的 {stopping}。</p>}
      <button type="button" disabled={busy} onClick={() => void onStart(choice)}
        className="mt-4 inline-flex h-9 items-center gap-1.5 rounded-full bg-primary-500 px-5 text-[13px] font-medium text-white shadow-[0_1px_2px_rgba(116,42,79,0.25),0_4px_12px_rgba(163,61,112,0.18)] hover:bg-primary-600 disabled:opacity-60">
        {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}{busy ? '开始中…' : '开始翻译'}
      </button>
    </div>
  );
}
```

- [ ] **Step 3: 提交**

```bash
git add src/features/articles/components/VersionTabs.tsx src/features/articles/components/CompareEmpty.tsx
git commit -m "feat(workbench): compare tabs and empty compare state"
```

---

### Task 11: PaneGrid 外观与只读

**Files:** `src/features/articles/components/PaneGrid.tsx`

- [ ] **Step 1: 改 `PaneColumn`**（接口里加）

```ts
  /** 主译本栏：极浅暖底 + 栏头顶部梅红细线 */
  primary?: boolean;
  /** 这一版只读（重翻中、还没出译文） */
  readOnly?: boolean;
  /** 收起竖条上的状态圆点 */
  tone?: Tone;
  /** 换了版本时整栏重新挂载，编辑框不会带着上一版的草稿 */
  versionKey?: string;
  /** 有它就显示它，不显示段落（对照栏没有别的版本时） */
  empty?: ReactNode;
```

import 加 `import type { Tone } from '../lib/versions';` 和 `import { TONE_DOT } from './StatusLine';`。

- [ ] **Step 2: 改 `PaneGrid` 的 return**：外面套一张「纸」，栏头和正文都在纸里

```tsx
  return (
    <div ref={container} className="flex min-h-0 flex-1 flex-col overflow-hidden md:px-[22px] md:pb-[22px]" data-testid="pane-grid">
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-white md:rounded-[14px] md:shadow-[0_1px_2px_rgba(43,39,48,0.05),0_10px_30px_rgba(43,39,48,0.06)]">
        <div className="z-20 grid shrink-0 border-b border-border-subtle bg-white" style={{ gridTemplateColumns: template }}>
          {visible.map(id => (
            <div key={id} className={cn('relative min-w-0 border-r border-border-subtle last:border-r-0',
              isCollapsed(id) ? 'bg-bg-tertiary' : columns[id].primary && 'bg-[#fdfaf9] before:absolute before:inset-x-0 before:top-0 before:h-0.5 before:bg-gradient-to-r before:from-primary-300 before:to-primary-500')}>
              {isCollapsed(id) ? (
                <button type="button" onClick={() => onToggle(id)} aria-label={`展开${columns[id].title}`}
                  className="flex h-full min-h-[44px] w-full flex-col items-center gap-2 py-3 text-text-muted hover:text-primary-700">
                  <ChevronRight className="h-4 w-4" />
                  {columns[id].tone && <span aria-hidden className={cn('h-1.5 w-1.5 rounded-full', TONE_DOT[columns[id].tone!])} />}
                </button>
              ) : (
                <div className="flex items-start gap-1 px-[22px] pb-4 pt-5 md:px-[26px]">
                  <div className="min-w-0 flex-1">{columns[id].header}</div>
                  {!mobilePane && (
                    <button type="button" onClick={() => onToggle(id)} aria-label={`收起${columns[id].title}`} title="收起这一栏"
                      className="-mr-2 -mt-1 rounded-lg p-2 text-text-muted hover:bg-[rgba(43,39,48,0.05)] hover:text-text-primary">
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="grid min-h-0 flex-1" style={{ gridTemplateColumns: template }}>
          {visible.map(id => isCollapsed(id) ? (
            <div key={id} className="border-r border-border-subtle bg-bg-tertiary last:border-r-0">
              <span className="block py-3 text-center text-xs tracking-[0.3em] text-text-muted [writing-mode:vertical-rl]">{columns[id].title}</span>
            </div>
          ) : (
            <article key={`${id}:${columns[id].versionKey ?? ''}`} aria-label={`${columns[id].title}正文`} data-version-fade=""
              className={cn('min-w-0 overflow-y-auto overscroll-contain border-r border-border-subtle px-[22px] pb-24 pt-6 last:border-r-0 md:px-[30px]',
                columns[id].primary && 'bg-[#fdfaf9]')}>
              {columns[id].empty ?? blocks.map(block => <ReadingBlock key={block[0].key} block={block} column={columns[id]}
                marked={block.some(row => row.key === readingKey)} markBusy={markBusy} onMark={onMark} />)}
            </article>
          ))}
        </div>
      </div>
    </div>
  );
```

- [ ] **Step 3: 改 `ReadingBlock`**

`showAdopt` 那行改成（只读的栏不往里采用）：

```ts
  const showAdopt = comparison && !column.readOnly && first.kind !== 'image' && (!complete || candidates.length > 0);
```

最外层 `div` 的 className 改成（标记改成左侧一道梅红细线；悬停只淡淡衬一下这一段）：

```tsx
      className={cn('group/reading relative mx-auto mb-5 max-w-[70ch] scroll-mt-8 rounded-md transition-colors [@media(hover:hover)]:hover:bg-[#fcf7f8]',
        marked && 'before:absolute before:-left-3 before:bottom-1 before:top-1 before:w-0.5 before:rounded-full before:bg-primary-500')}>
```

- [ ] **Step 4: 改 `Cell`**

`const textClass = rowTextClass(row);` 改成：

```ts
  const textClass = rowTextClass(row, column.id === 'source' ? 'en' : 'zh');
```

`ReadingBlock` 里 `inline ? <div className={rowTextClass(first)}>` 同样改成 `rowTextClass(first, column.id === 'source' ? 'en' : 'zh')`。

`<EditableText … />` 加一个属性：`readOnly={column.readOnly}`。

- [ ] **Step 5: 换版本时淡入**（设计文档 5.4：对调主译本、切换对照标签时整栏重新挂载，淡入 200ms；减少动态效果时不动）

`src/styles/fluid-theme.css` 末尾加：

```css
@keyframes workbench-version-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (prefers-reduced-motion: no-preference) {
  [data-version-fade] { animation: workbench-version-fade 200ms ease-out; }
}
```

- [ ] **Step 6:** `npx eslint src/features/articles/components/PaneGrid.tsx` → 无错误（Workbench 还没改，tsc 仍有它的错，下一个 Task 处理）
- [ ] **Step 7: 提交**

```bash
git add src/styles/fluid-theme.css src/features/articles/components/PaneGrid.tsx
git commit -m "feat(workbench): book-page sheet, primary tint, read-only and collapsed status dots"
```

---

### Task 12: 顶栏和工作台本体

**Files:**
- Create: `src/features/articles/components/WorkbenchTopBar.tsx`
- Modify（整个重写）: `src/features/articles/components/Workbench.tsx`
- Modify: `src/features/articles/articles.test.tsx`

- [ ] **Step 1: 先改测试**（`articles.test.tsx`）

1. `api` 加 `setPrimary: vi.fn()`；skills api 的 mock 换成带 `models`：

```tsx
const models = vi.hoisted(() => vi.fn());
vi.mock('@/features/skills/api', async importOriginal => {
  const actual = await importOriginal<typeof import('@/features/skills/api')>();
  return { ...actual, skillsApi: { ...actual.skillsApi, stop: stopAgent, models } };
});
```

`beforeEach` 里加：

```tsx
  models.mockReset();
  models.mockResolvedValue({ models: [{ id: 'gpt-5.5-codex', label: 'gpt-5.5-codex', description: '' }], default_model: 'gpt-5.5', source: 'cache', warning: null });
  api.setPrimary.mockResolvedValue({ ok: true });
```

顶部 import 加 `import { AlignmentTooLow } from './lib/claude';`。再加两个工具函数（放在 `flush` 下面）：

```tsx
const inPopover = () => document.body.querySelector('[role="dialog"]') as HTMLElement;
const buttonIn = (root: ParentNode, text: string) =>
  Array.from(root.querySelectorAll('button')).find(b => b.textContent?.trim() === text) as HTMLButtonElement;
```

2. 全文替换：`译本 1正文` → `主译本正文`；`编辑：译本 1：` → `编辑：主译本：`；`译本 1：从这里继续阅读` → `主译本：从这里继续阅读`。

3. `DATA.project` 加 `primary: 'p1', primary_target: null`。新增一份带 Codex 版的数据（放在 `DATA` 下面）：

```tsx
const WITH_CODEX: WorkbenchData = {
  ...DATA,
  variants: [...DATA.variants, {
    id: 'p1--codex', kind: 'claude', label: 'Codex', title_translation: null, progress: { total: 2, approved: 0 },
    status: { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null },
    import: { run_id: 'r0', agent: 'codex', model: 'gpt-5.5', aligned: 2, unaligned: 0, merged_blocks: 0, imported_at: '2026-10-28T10:00:00' },
  }],
  rows: DATA.rows.map(row => ({ ...row, alt: { ...row.alt, 'p1--codex': row.kind === 'image' ? null : `码·${row.source}` } })),
};
```

4. 前两条（选 Agent / 停旧任务）整个换成：

```tsx
  it('adds a new agent from ＋ and waits for the old run to stop before starting it', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'old-run' } });
    agentRun.current = runningAgent;
    let finishStop!: () => void;
    stopAgent.mockImplementation(() => new Promise<RunMeta>(resolve => {
      finishStop = () => resolve({ ...runningAgent, status: 'error', error: '任务已停止' });
    }));
    claude.startClaudeTrack.mockResolvedValue({ ...runningAgent, id: 'new-run', harness: 'antigravity' });
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="用 Agent 再翻一版"]') as HTMLButtonElement).click(); });
    await flush();
    const popover = inPopover();
    const gemini = Array.from(popover.querySelectorAll('[role="radiogroup"][aria-label="Agent"] [role="radio"]'))
      .find(el => el.textContent?.includes('Gemini')) as HTMLButtonElement;
    await act(async () => { gemini.click(); });
    expect(popover.textContent).toContain('会先停掉正在跑的 Codex');
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
    const start = buttonIn(popover, '开始翻译');
    await act(async () => { start.click(); start.click(); });
    expect(skillsApi.stop).toHaveBeenCalledExactlyOnceWith('old-run');
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
    await act(async () => { finishStop(); });
    expect(claude.startClaudeTrack).toHaveBeenCalledExactlyOnceWith('p1', { harness: 'antigravity', model: '' }, '2027 数据中心');
    expect(claude.importClaudeTrack).not.toHaveBeenCalled();
  });

  it('does not launch a replacement when stopping the old run fails', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'old-run' } });
    agentRun.current = runningAgent;
    stopAgent.mockRejectedValue(new Error('旧任务未停止'));
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="用 Agent 再翻一版"]') as HTMLButtonElement).click(); });
    await flush();
    await act(async () => { buttonIn(inPopover(), '开始翻译').click(); });
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('旧任务未停止');
  });
```

5. 「persists a reading mark…」里点「继续阅读」那一行换成先打开书签弹框：

```tsx
    await act(async () => { (host.querySelector('button[aria-label="阅读标记"]') as HTMLButtonElement).click(); });
    await act(async () => { buttonIn(inPopover(), '继续阅读').click(); });
```

「keeps the previous reading mark when saving fails」里点 `清除阅读标记` 那一行换成：

```tsx
    await act(async () => { (host.querySelector('button[aria-label="阅读标记"]') as HTMLButtonElement).click(); });
    await act(async () => { (inPopover().querySelector('[aria-label="清除阅读标记"]') as HTMLButtonElement).click(); });
```

6. 「saves on demand…」里：`saveButton` 换成 `host.querySelector('button[aria-label="保存"]') as HTMLButtonElement`；
「看你改了什么」换成：

```tsx
    await act(async () => { (host.querySelector('button[aria-label="主译本的更多操作"]') as HTMLButtonElement).click(); });
    await act(async () => { buttonIn(inPopover(), '看我改了什么').click(); });
```

7. 「treats an agent that ended its turn asking for confirmation as waiting…」的两条 `expect` 换成：

```tsx
    expect(host.textContent).toContain('等你确认');
    expect(host.textContent).toContain('前不回复就按它的建议继续');
    expect(host.textContent).toContain('去确认');
```

8. 新增（放在 `describe('Workbench')` 末尾）：

```tsx
  it('keeps the primary version in the middle and swaps it with 设为主译本', async () => {
    api.workbench.mockResolvedValue(WITH_CODEX);
    await render(<Workbench projectId="p1" />);
    await flush();
    const main = () => host.querySelector('[aria-label="主译本正文"]')!;
    const compare = () => host.querySelector('[aria-label="对照正文"]')!;
    expect(main().textContent).toContain('数据中心正在爆发。');
    expect(compare().textContent).toContain('码·Datacenters are booming.'); // 对照默认是最近导入的 Codex 版
    expect(host.textContent).toContain('已完成 · gpt-5.5');
    await act(async () => { buttonIn(host, '设为主译本').click(); });
    await flush();
    expect(api.setPrimary).toHaveBeenCalledWith('p1', 'p1--codex');
    expect(main().textContent).toContain('码·Datacenters are booming.');
    expect(compare().textContent).toContain('数据中心正在爆发。');
  });

  it('locks the primary agent version while it is being re-translated', async () => {
    api.workbench.mockResolvedValue({ ...WITH_CODEX, project: { ...WITH_CODEX.project, primary: 'p1--codex', claude_run_id: 'run-2' } });
    agentRun.current = { ...runningAgent, id: 'run-2', model: 'gpt-5.5-codex' };
    await render(<Workbench projectId="p1" />);
    await flush();
    const main = host.querySelector('[aria-label="主译本正文"]')!;
    expect(main.querySelectorAll('[aria-label^="编辑："]')).toHaveLength(0);
    expect(host.textContent).toContain('重翻中 · gpt-5.5-codex · 翻完前只读');
    expect(main.textContent).not.toContain('采用');
  });

  it('retranslates an agent version with another model and warns about edits that will be replaced', async () => {
    api.workbench.mockResolvedValue(WITH_CODEX);
    api.changes.mockResolvedValue({ total: 2, changed: 2, changes: [] });
    claude.startClaudeTrack.mockResolvedValue({ ...runningAgent, id: 'new-run' });
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="重新翻译"]') as HTMLButtonElement).click(); });
    await flush();
    const popover = inPopover();
    expect(popover.textContent).toContain('你改过的 2 段也会被替换');
    const option = Array.from(popover.querySelectorAll('[role="radiogroup"][aria-label="模型"] [role="radio"]'))
      .find(el => el.textContent?.includes('gpt-5.5-codex')) as HTMLButtonElement;
    await act(async () => { option.click(); });
    await act(async () => { buttonIn(popover, '重新翻译').click(); });
    await flush();
    expect(claude.startClaudeTrack).toHaveBeenCalledWith('p1', { harness: 'codex', model: 'gpt-5.5-codex' }, '2027 数据中心');
  });

  it('offers 继续翻译 only for an unfinished web version, never 重新翻译', async () => {
    const partial = { ...DATA, rows: DATA.rows.map(row => row.key === 's1/p000' ? { ...row, web: null } : row) };
    api.workbench.mockResolvedValue(partial);
    api.startWorkflow.mockResolvedValue({ run_id: 'r' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.querySelector('[aria-label="重新翻译"]')).toBeNull();
    expect(host.textContent).toContain('缺 1 段');
    await act(async () => { buttonIn(host, '继续翻译').click(); });
    await flush();
    expect(api.startWorkflow).toHaveBeenCalledWith('p1', { model: undefined, autoAcceptTerms: true, sectionIds: ['s1'] });
  });

  it('does not import a draft that does not match the download until asked to', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'run-3' } });
    agentRun.current = { ...runningAgent, id: 'run-3', status: 'idle' };
    claude.importClaudeTrack
      .mockRejectedValueOnce(new AlignmentTooLow('Agent 的英文稿只对上 1/3 段，可能不是这篇下载的原文'))
      .mockResolvedValueOnce({ variant_id: 'p1--codex', aligned: 3, unaligned: 0 });
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.textContent).toContain('没导入：Agent 的英文稿只对上 1/3 段');
    await act(async () => { buttonIn(host, '仍然导入').click(); });
    await flush();
    expect(claude.importClaudeTrack).toHaveBeenLastCalledWith('p1', agentRun.current, true);
  });

  it('offers an agent right in the compare column when there is nothing to compare', async () => {
    api.workbench.mockResolvedValue({ ...DATA, variants: [] });
    await render(<Workbench projectId="p1" />);
    await flush();
    const compare = host.querySelector('[aria-label="对照正文"]')!;
    expect(compare.textContent).toContain('选一个 Agent 翻这篇');
    expect(buttonIn(compare, '开始翻译')).toBeDefined();
  });
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `npx vitest run src/features/articles/articles.test.tsx`
Expected: FAIL（还是旧 Workbench）

- [ ] **Step 3: `WorkbenchTopBar.tsx`**

```tsx
import { useState, type ReactNode } from 'react';
import { ArrowLeft, Bookmark, ChevronDown, Download, ExternalLink, FileDiff, MoreHorizontal, PanelLeft, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { HUMAN_EDITS_URL } from '../api';
import { IconAction } from './VersionHeader';

export interface ExportItem {
  label: string;
  onSelect: () => void;
}

/** 顶栏：标题、保存状态、阅读标记、导出主译本、更多。和页面底色融为一体，不画边框。 */
export function WorkbenchTopBar({ title, original, onShowList, onBack, save, mark, onJump, onClearMark, markBusy,
  onExportPrimary, exportItems, legacyHref, originalUrl }: {
  title: string;
  original: string | null;
  onShowList?: () => void;
  onBack: () => void;
  save: ReactNode;
  /** 标记处的文字；null = 没有标记 */
  mark: string | null;
  onJump: () => void;
  onClearMark: () => void;
  markBusy: boolean;
  onExportPrimary: () => void;
  exportItems: ExportItem[];
  legacyHref: string;
  originalUrl: string | null;
}) {
  const [markOpen, setMarkOpen] = useState(false);
  return (
    <header className="flex items-center gap-3 px-4 pb-3.5 pt-4 md:px-[26px]">
      {onShowList
        ? <IconAction label="显示文章列表" onClick={onShowList}><PanelLeft className="h-4 w-4" /></IconAction>
        : <IconAction label="回到文章列表" onClick={onBack}><ArrowLeft className="h-4 w-4" /></IconAction>}
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-[19px] font-semibold leading-snug tracking-[0.01em] text-text-primary [font-family:var(--font-display)]" title={original ?? title}>{title}</h1>
        {original && <p className="truncate text-[13px] italic text-text-muted [font-family:var(--font-source)]">{original}</p>}
      </div>
      {save}
      {mark !== null && (
        <Popover open={markOpen} onOpenChange={setMarkOpen}>
          <PopoverTrigger asChild>
            <IconAction label="阅读标记" className="text-primary-500"><Bookmark className="h-4 w-4 fill-current" /></IconAction>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-72 rounded-xl p-3">
            <p className="text-[11px] tracking-[0.12em] text-text-muted">看到这里</p>
            <p className="mt-1 line-clamp-3 text-[13px] leading-relaxed text-text-primary [font-family:var(--font-display)]">{mark}</p>
            <div className="mt-3 flex items-center justify-between">
              <button type="button" aria-label="清除阅读标记" disabled={markBusy} onClick={() => { setMarkOpen(false); onClearMark(); }}
                className="inline-flex items-center gap-1 text-[12px] text-text-muted hover:text-text-primary disabled:opacity-40">
                <X className="h-3.5 w-3.5" />清除
              </button>
              <button type="button" onClick={() => { setMarkOpen(false); onJump(); }}
                className="rounded-full bg-primary-50 px-3 py-1 text-[12.5px] text-primary-700 hover:bg-primary-100">继续阅读</button>
            </div>
          </PopoverContent>
        </Popover>
      )}
      <div className="inline-flex items-stretch overflow-hidden rounded-full bg-primary-500 text-[13px] font-medium text-white shadow-[0_1px_2px_rgba(116,42,79,0.25),0_4px_12px_rgba(163,61,112,0.18)]">
        <button type="button" onClick={onExportPrimary} className="inline-flex items-center gap-1.5 py-2 pl-4 pr-3.5 hover:bg-primary-600">
          <Download className="h-3.5 w-3.5" /><span className="hidden sm:inline">导出主译本</span>
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" aria-label="导出其他版本" className="border-l border-white/30 px-2.5 hover:bg-primary-600"><ChevronDown className="h-3.5 w-3.5" /></button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {exportItems.map(item => <DropdownMenuItem key={item.label} onSelect={item.onSelect}>{item.label}</DropdownMenuItem>)}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <IconAction label="更多"><MoreHorizontal className="h-4 w-4" /></IconAction>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          {originalUrl && (
            <DropdownMenuItem asChild>
              <a href={originalUrl} target="_blank" rel="noreferrer"><ExternalLink className="h-4 w-4" /> 原文链接</a>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem asChild><Link to={legacyHref}>旧版编辑器（单段重译、质量报告）</Link></DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild><a href={HUMAN_EDITS_URL}><FileDiff className="h-4 w-4" /> 下载全部文章的人工改动</a></DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
```

- [ ] **Step 4: `Workbench.tsx` 整个换成**

```tsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Plus, RefreshCw, Star } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { harnessLabel } from '@/features/skills/harness';
import { skillsApi } from '@/features/skills/api';
import { isUnauthorized } from '@/features/skills/hooks';
import type { RunMeta } from '@/features/skills/types';
import { articlesApi, downloadText } from '../api';
import { articleKeys, useClaudeRun, useWorkbench } from '../hooks';
import { saveAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { AlignmentTooLow, importClaudeTrack, startClaudeTrack } from '../lib/claude';
import { flushEdits, unsavedEdits } from '../lib/edits';
import { loadCollapsed, PANES, saveCollapsed, togglePane, type Collapsed } from '../lib/panes';
import { sectionsWithMissing } from '../lib/tracks';
import { buildVersions, defaultCompare, pickPrimary, runActive, type ImportProblem, type VersionAction, type VersionView } from '../lib/versions';
import type { PaneId, Workbench as WorkbenchData, WorkbenchRow } from '../types';
import { ChangesDrawer, type ChangesTarget } from './ChangesDrawer';
import { ColumnMenu, type MenuItem } from './ColumnMenu';
import { CompareEmpty } from './CompareEmpty';
import { PaneGrid, type PaneColumn } from './PaneGrid';
import { SaveStatus } from './SaveStatus';
import { StatusLine } from './StatusLine';
import { TrackDrawer, type DrawerState } from './TrackDrawer';
import { AddAgentPopover, RetranslatePopover } from './TranslatePopovers';
import { IconAction, VersionHeader, VersionName } from './VersionHeader';
import { VersionTabs } from './VersionTabs';
import { WorkbenchTopBar } from './WorkbenchTopBar';

function useIsMobile(): boolean {
  const query = '(max-width: 767px)';
  const [mobile, setMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia?.(query)?.matches);
  useEffect(() => {
    const list = window.matchMedia?.(query);
    if (!list) return;
    const update = () => setMobile(list.matches);
    list.addEventListener('change', update);
    return () => list.removeEventListener('change', update);
  }, []);
  return Boolean(mobile);
}

function isQaBlocked(error: unknown): boolean {
  return error instanceof Error && error.message.includes('QA');
}

interface WorkbenchProps {
  projectId: string;
  onShowList?: () => void;
}

export function Workbench({ projectId, onShowList }: WorkbenchProps) {
  const query = useWorkbench(projectId);
  if (query.isPending) {
    return <div className="flex h-full items-center justify-center text-sm text-text-muted">读取文章…</div>;
  }
  if (query.error || !query.data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-text-muted">
        <p>打不开这篇文章：{query.error?.message ?? '未知错误'}</p>
        <Link to="/articles" className="text-primary-700 underline">回到文章列表</Link>
      </div>
    );
  }
  return <WorkbenchView key={projectId} data={query.data} onShowList={onShowList} />;
}

function WorkbenchView({ data, onShowList }: { data: WorkbenchData; onShowList?: () => void }) {
  const { project, rows } = data;
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState<Collapsed>(loadCollapsed);
  const [mobilePane, setMobilePane] = useState<PaneId>('main');
  const [compareId, setCompareId] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<DrawerState>(null);
  const [changes, setChanges] = useState<ChangesTarget | null>(null);
  const [importProblem, setImportProblem] = useState<ImportProblem | null>(null);
  const [busy, setBusy] = useState(false);
  const agentStartLock = useRef(false);
  const [saving, setSaving] = useState(false);
  const [markBusy, setMarkBusy] = useState(false);
  const [readingJump, setReadingJump] = useState(0);
  const markLock = useRef(false);
  const importTried = useRef<string | null>(null);

  const claudeRun = useClaudeRun(project.claude_run_id);
  const run = claudeRun.data;
  const needsLogin = Boolean(project.claude_run_id) && isUnauthorized(claudeRun.error);
  const { versions, addable } = useMemo(
    () => buildVersions({ data, run, needsLogin, importProblem }), [data, run, needsLogin, importProblem]);
  const primary = pickPrimary(versions, project.primary);
  const others = versions.filter(version => version.id !== primary.id);
  const compare = others.find(version => version.id === compareId) ?? defaultCompare(versions, primary, run);
  const title = project.title_translation || primary.variant?.title_translation || project.title;
  const stopping = run && runActive(run) ? harnessLabel(run.harness) : null;
  const words = useMemo(() => rows.reduce(
    (count, row) => (row.kind === 'image' ? count : count + (row.source.match(/[A-Za-z0-9][A-Za-z0-9'’.-]*/g)?.length ?? 0)), 0), [rows]);
  const refresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: articleKeys.workbench(project.id) }),
    [queryClient, project.id],
  );

  // 离开页面时还有没存下的修改就提醒
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!unsavedEdits.any()) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, []);

  const importRun = useCallback(async (target: RunMeta, force: boolean) => {
    try {
      const result = await importClaudeTrack(project.id, target, force);
      toast.success(`${harnessLabel(target.harness)} 译文已导入：对上 ${result.aligned} 段`);
      setImportProblem(null);
      await refresh();
    } catch (error) {
      setImportProblem({ runId: target.id, alignment: error instanceof AlignmentTooLow,
        message: error instanceof Error ? error.message : '导入失败' });
    }
  }, [project.id, refresh]);

  // Agent 一轮结束、不是在等你确认、还没导入：自动取回 zh.md 导入（每个任务只自动试一次）
  useEffect(() => {
    if (!run || run.status !== 'idle' || run.awaiting_reply || importTried.current === run.id) return;
    if (data.variants.some(variant => variant.import?.run_id === run.id)) return;
    importTried.current = run.id;
    void importRun(run, false);
  }, [run, data.variants, importRun]);

  const toggle = (pane: PaneId) => {
    setCollapsed(current => {
      const next = togglePane(current, pane);
      saveCollapsed(next);
      return next;
    });
  };

  const save = useCallback(async (target: string, row: WorkbenchRow, text: string) => {
    await articlesApi.saveText(project.id, { target, section_id: row.section_id, paragraph_id: row.paragraph_id, text });
    queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
      ...current,
      rows: current.rows.map(item => item.key !== row.key ? item : target === project.id
        ? { ...item, web: text }
        : { ...item, alt: { ...item.alt, [target]: text } }),
    });
  }, [project.id, queryClient]);

  const markReading = async (key: string | null) => {
    if (markLock.current) return;
    markLock.current = true;
    setMarkBusy(true);
    try {
      await queryClient.cancelQueries({ queryKey: articleKeys.workbench(project.id) });
      const result = await articlesApi.setReadingMark(project.id, key);
      queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
        ...current, reading_mark: result.reading_mark,
      });
      toast.success(key ? '已标记：看到这里' : '已清除阅读标记');
    } catch (error) {
      toast.error(`阅读标记没保存上：${error instanceof Error ? error.message : '请重试'}`);
    } finally {
      markLock.current = false;
      setMarkBusy(false);
    }
  };

  const exportVersion = async (target: string, format: 'zh' | 'en') => {
    try {
      const result = await articlesApi.exportMarkdown(target, format);
      downloadText(result.filename, result.content);
    } catch (error) {
      if (format === 'zh' && isQaBlocked(error) && window.confirm(`${(error as Error).message}\n\n仍然导出？`)) {
        const result = await articlesApi.exportMarkdown(target, format, true);
        downloadText(result.filename, result.content);
        return;
      }
      toast.error(error instanceof Error ? error.message : '导出失败');
    }
  };

  /** 手动保存：改动本来就自动保存，这里只是让正在改的那段立刻存下，并确认都存好了 */
  const saveNow = useCallback(async () => {
    setSaving(true);
    try {
      if (await flushEdits()) toast.success('已保存');
      else toast.error('有段落没保存上（标红的那几段），点它旁边的「重试」');
    } finally {
      setSaving(false);
    }
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        void saveNow();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [saveNow]);

  const continueTranslation = async (version: VersionView) => {
    try {
      if (version.source === 'web' && !rows.some(row => row.web)) {
        await articlesApi.startWorkflow(project.id);
        toast.success('网页版开始翻译');
      } else {
        const sections = sectionsWithMissing(rows, version.text);
        if (!sections.length) return;
        const names = sections.map(section => `「${section.title}」`).join('、');
        if (!window.confirm(`重译缺译段落所在的 ${sections.length} 章：${names}\n\n这几章里已有的译文（包括你改过的）会被新译文替换，其他章节不动。继续？`)) return;
        await articlesApi.startWorkflow(version.id, { model: version.fillModel, autoAcceptTerms: true, sectionIds: sections.map(section => section.id) });
        toast.success(`开始重译 ${sections.length} 章`);
      }
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能开始');
    }
  };

  /** 交给 Agent：有旧任务先停干净再开新的。成功返回 true（弹框据此关掉）。 */
  const startAgent = async (choice: AgentChoice): Promise<boolean> => {
    if (agentStartLock.current) return false;
    agentStartLock.current = true;
    setBusy(true);
    try {
      if (project.claude_run_id) {
        // 防止停下来的半成品被当成结果导入
        importTried.current = project.claude_run_id;
        const stopped = await skillsApi.stop(project.claude_run_id);
        queryClient.setQueryData(articleKeys.claudeRun(stopped.id), stopped);
      }
      const nextRun = await startClaudeTrack(project.id, choice, title);
      saveAgentChoice(choice);
      queryClient.setQueryData(articleKeys.claudeRun(nextRun.id), nextRun);
      queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
        ...current, project: { ...current.project, claude_run_id: nextRun.id },
      });
      setImportProblem(null);
      importTried.current = null;
      const versionId = `${project.id}--${choice.harness}`;
      if (versionId !== primary.id) setCompareId(versionId);
      toast.success(`已交给 ${harnessLabel(choice.harness)}；它需要你确认时这里会提示`);
      await refresh();
      return true;
    } catch (error) {
      toast.error(isUnauthorized(error) ? '先去 Agent 页登录一次（只需一次）' : error instanceof Error ? error.message : '没能交出去');
      return false;
    } finally {
      agentStartLock.current = false;
      setBusy(false);
    }
  };

  const makePrimary = async (version: VersionView) => {
    if (!(await flushEdits())) {
      toast.error('有段落没保存上，先处理再换主译本');
      return;
    }
    const previous = primary.id;
    try {
      await articlesApi.setPrimary(project.id, version.id);
      queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
        ...current, project: { ...current.project, primary_target: version.id, primary: version.id },
      });
      setCompareId(previous);
      toast.success(`主译本改为 ${version.name}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能设为主译本');
    }
  };

  const switchCompare = async (id: string) => {
    if (id === compare?.id) return;
    if (!(await flushEdits())) {
      toast.error('有段落没保存上，先处理再切换');
      return;
    }
    setCompareId(id);
  };

  const onAction = (version: VersionView, action: VersionAction) => {
    if (action.kind === 'confirm-terms') setDrawer({ kind: 'terms', projectId: version.id, jobId: action.jobId });
    else if (action.kind === 'open-run' && run) setDrawer({ kind: 'claude', run });
    else if (action.kind === 'continue') void continueTranslation(version);
    else if (action.kind === 'login') navigate('/skills');
    else if (action.kind === 'force-import' && run) void importRun(run, true);
  };

  const menuFor = (version: VersionView): MenuItem[] => [
    ...(version.pending ? [] : [{ label: '看我改了什么', onSelect: () => setChanges({ projectId: project.id, target: version.id, label: version.name, title }) }]),
    ...(version.harness && run && (run.harness ?? 'claude') === version.harness
      ? [{ label: `看 ${version.name} 的对话`, onSelect: () => setDrawer({ kind: 'claude', run }) }] : []),
  ];

  const retranslate = (version: VersionView) => version.translate === 'retranslate' && version.harness ? (
    <RetranslatePopover projectId={project.id} version={version} stopping={stopping} busy={busy}
      onConfirm={model => startAgent({ harness: version.harness!, model })}>
      <IconAction label="重新翻译"><RefreshCw className="h-4 w-4" /></IconAction>
    </RetranslatePopover>
  ) : null;

  const placeholder = (version: VersionView) =>
    version.pending ? '译文还没出来' : version.tone === 'busy' ? '翻译中…' : '还没有译文，可以直接写';

  const columns: Record<PaneId, PaneColumn> = {
    source: {
      id: 'source',
      title: '英文',
      header: <VersionHeader eyebrow="原文" title={<VersionName english>English</VersionName>}
        line={<p className="mt-1.5 text-[12px] text-text-muted">{words.toLocaleString('en-US')} 词</p>} />,
    },
    main: {
      id: 'main',
      title: '主译本',
      primary: true,
      versionKey: primary.id,
      tone: primary.tone,
      readOnly: primary.readOnly,
      header: <VersionHeader primary eyebrow="主译本" title={<VersionName>{primary.name}</VersionName>}
        line={<StatusLine version={primary} onAction={action => onAction(primary, action)} />}
        actions={<>{retranslate(primary)}<ColumnMenu label="主译本的更多操作" items={menuFor(primary)} /></>} />,
      text: primary.text,
      save: (row, text) => save(primary.id, row, text),
      placeholder: placeholder(primary),
      adopt: compare && !compare.pending ? { label: compare.name, text: compare.text } : undefined,
    },
    compare: compare ? {
      id: 'compare',
      title: '对照',
      versionKey: compare.id,
      tone: compare.tone,
      readOnly: compare.readOnly || compare.pending,
      header: <VersionHeader eyebrow="对照"
        title={<VersionTabs versions={others} value={compare.id} onChange={id => void switchCompare(id)} forceMenu={isMobile}
          add={addable.length ? (
            <AddAgentPopover options={addable} stopping={stopping} busy={busy} onConfirm={startAgent}>
              <button type="button" aria-label="用 Agent 再翻一版" title="用 Agent 再翻一版"
                className="inline-flex items-center rounded-full px-2.5 py-1 text-primary-700 hover:bg-white/70"><Plus className="h-3.5 w-3.5" /></button>
            </AddAgentPopover>
          ) : null} />}
        line={<StatusLine version={compare} onAction={action => onAction(compare, action)} />}
        actions={<>
          {retranslate(compare)}
          {!compare.pending && (
            <button type="button" onClick={() => void makePrimary(compare)}
              className="inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-[12.5px] text-primary-700 hover:bg-primary-50">
              <Star className="h-3.5 w-3.5" />设为主译本
            </button>
          )}
          <ColumnMenu label="对照的更多操作" items={menuFor(compare)} />
        </>} />,
      text: compare.text,
      save: (row, text) => save(compare.id, row, text),
      placeholder: placeholder(compare),
      adopt: { label: primary.name, text: primary.text },
    } : {
      id: 'compare',
      title: '对照',
      header: <VersionHeader eyebrow="对照" title={<VersionName>还没有别的版本</VersionName>}
        line={<p className="mt-1.5 text-[12px] text-text-muted">用 Agent 翻一版，就能左右对照</p>} />,
      text: () => null,
      save: async () => undefined,
      readOnly: true,
      empty: <CompareEmpty options={addable} stopping={stopping} busy={busy} onStart={startAgent} />,
    },
  };

  const markRow = data.reading_mark ? rows.find(row => row.key === data.reading_mark?.key) : undefined;
  const markText = data.reading_mark ? (primary.text(markRow ?? rows[0]) || markRow?.source || '已标记的位置') : null;
  const exportItems = [
    { label: '英文原文', onSelect: () => void exportVersion(project.id, 'en') },
    ...versions.filter(version => !version.pending).map(version => ({
      label: `${version.name}${version.model ? `（${version.model}）` : ''}${version.id === primary.id ? ' · 主译本' : ''}`,
      onSelect: () => void exportVersion(version.id, 'zh'),
    })),
  ];

  return (
    <div className="flex h-full min-h-0 flex-col bg-bg-primary">
      <WorkbenchTopBar title={title} original={title !== project.title ? project.title : null}
        onShowList={onShowList} onBack={() => navigate('/articles')}
        save={<SaveStatus saving={saving} onSave={() => void saveNow()} />}
        mark={markText} onJump={() => setReadingJump(n => n + 1)} onClearMark={() => void markReading(null)} markBusy={markBusy}
        onExportPrimary={() => void exportVersion(primary.id, 'zh')} exportItems={exportItems}
        legacyHref={`/document/${project.id}`} originalUrl={project.original_url} />

      {isMobile && (
        <div className="mx-4 mb-2 grid grid-cols-3 rounded-full bg-[#f5eff1] p-[3px] text-[13px]" role="tablist" aria-label="切换栏">
          {PANES.map(id => (
            <button key={id} type="button" role="tab" aria-selected={mobilePane === id} onClick={() => setMobilePane(id)}
              className={cn('rounded-full py-1', mobilePane === id ? 'bg-white text-text-primary shadow-sm' : 'text-text-muted')}>
              {columns[id].title}
            </button>
          ))}
        </div>
      )}

      <PaneGrid rows={rows} columns={columns} collapsed={collapsed} onToggle={toggle} mobilePane={isMobile ? mobilePane : null}
        readingKey={data.reading_mark?.key} markBusy={markBusy} onMark={key => void markReading(key)} jump={readingJump} />

      <TrackDrawer state={drawer} mainId={project.id} onClose={() => { setDrawer(null); void refresh(); void claudeRun.refetch(); }} />
      <ChangesDrawer state={changes} onClose={() => setChanges(null)} />
    </div>
  );
}
```

- [ ] **Step 5: 跑测试**

Run: `npx vitest run src/features/articles`
Expected: 全部通过。常见问题：
- Radix Popover 内容在 `document.body`（Portal），断言要用 `inPopover()` 而不是 `host`。
- `已完成 · gpt-5.5` 这条断言依赖 Task 4 的 `line: ['已完成', 'gpt-5.5']`。

- [ ] **Step 6: 类型和 lint**

Run: `npx tsc -b && npm run lint`
Expected: 无错误（若 `ArticlePreview.tsx` / `importFlow.ts` 报 `startClaudeTrack` 签名错误，属于 Task 13，先做 Task 13 再回来跑）

- [ ] **Step 7: 提交**

```bash
git add src/features/articles/components/WorkbenchTopBar.tsx src/features/articles/components/Workbench.tsx src/features/articles/articles.test.tsx
git commit -m "feat(workbench): primary + compare columns with book-page header and per-version actions"
```

---

### Task 13: 导入页两个勾选

**Files:**
- Modify: `src/features/articles/lib/importFlow.ts`
- Modify: `src/features/articles/components/ArticlePreview.tsx`
- Delete: `src/features/articles/components/ArticleAgentChoice.tsx`
- Modify: `src/features/articles/articles.test.tsx`（`describe('importAndTranslate')`）

- [ ] **Step 1: 改测试**

`describe('importAndTranslate')` 里的三条换成：

```tsx
  const codex = { harness: 'codex' as const, model: 'gpt-5.5-codex' };

  it.each([
    [true, codex],
    [true, null],
    [false, codex],
    [false, null],
  ] as const)('web %s, agent %o', async (web, agent) => {
    await expect(importAndTranslate({ url: 'u', title: 'Demo', zh_title: '演示' }, { web, agent }, vi.fn())).resolves.toBe('p1');
    expect(api.startWorkflow.mock.calls).toEqual(web ? [['p1']] : []);
    // 对话标题用文章的中文标题
    expect(claude.startClaudeTrack.mock.calls).toEqual(agent ? [['p1', agent, '演示']] : []);
  });

  it('does not start anything again for an article imported before', async () => {
    substack.importArticle.mockResolvedValue({ project: { id: 'p1' }, already_imported: true });
    await importAndTranslate({ url: 'u' }, { web: true, agent: codex }, vi.fn());
    expect(api.startWorkflow).not.toHaveBeenCalled();
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
  });

  it('still opens the article when the agent cannot start', async () => {
    claude.startClaudeTrack.mockRejectedValue(new Error('skill-runner 挂了'));
    const notify = vi.fn();
    await expect(importAndTranslate({ url: 'u' }, { web: false, agent: { harness: 'claude', model: '' } }, notify)).resolves.toBe('p1');
    expect(notify).toHaveBeenCalledWith(expect.stringContaining('skill-runner 挂了'));
  });
```

- [ ] **Step 2:** `npx vitest run src/features/articles/articles.test.tsx -t importAndTranslate` → FAIL

- [ ] **Step 3: `importFlow.ts` 整个换成**

```ts
import { toast } from 'sonner';
import { substackApi, type SubstackArticle } from '@/features/substack/api';
import { isUnauthorized } from '@/features/skills/hooks';
import { articlesApi } from '../api';
import type { AgentChoice } from './agentChoice';
import { startClaudeTrack } from './claude';

/** 导入后翻哪几版：网页版要不要翻；Agent 用谁、什么模型（null = 不用 Agent）。两个都不要 = 只导入。 */
export interface ImportChoice {
  web: boolean;
  agent: AgentChoice | null;
}

/** 导入 → 按选择启动网页版和 Agent。某一路没能开始不挡住进工作台，只提示。返回主项目 id。 */
export async function importAndTranslate(
  article: Pick<SubstackArticle, 'url'> & Partial<Pick<SubstackArticle, 'title' | 'zh_title'>>,
  choice: ImportChoice,
  notify: (message: string) => void = message => toast.warning(message),
): Promise<string> {
  const imported = await substackApi.importArticle(article.url);
  const projectId = imported.project.id;
  if (imported.already_imported) return projectId;
  if (choice.web) {
    try {
      await articlesApi.startWorkflow(projectId);
    } catch (error) {
      notify(`网页版没能开始：${error instanceof Error ? error.message : error}`);
    }
  }
  if (choice.agent) {
    try {
      await startClaudeTrack(projectId, choice.agent, article.zh_title || article.title);
    } catch (error) {
      notify(isUnauthorized(error)
        ? '要先在 Agent 页登录一次：登录后在工作台里用「＋」交给 Agent'
        : `Agent 没能开始：${error instanceof Error ? error.message : error}`);
    }
  }
  return projectId;
}
```

- [ ] **Step 4: `ArticlePreview.tsx`**

import 区换成（去掉 `ARTICLE_HARNESSES`、`ArticleAgentChoice`、`Harness`、`runsAgent`、`ImportPlan`）：

```tsx
import { useState } from 'react';
import { ExternalLink, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { isCookieError, type SubstackArticle } from '@/features/substack/api';
import { CookieForm } from '@/features/substack/components/CookieForm';
import { ARTICLE_HARNESSES, loadAgentChoice, saveAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { importAndTranslate } from '../lib/importFlow';
import { AgentChoiceFields } from './AgentCards';
```

删掉 `PLANS` 常量。组件里的状态换成：

```tsx
  const [web, setWeb] = useState(true);
  const [useAgent, setUseAgent] = useState(true);
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice());
```

`start` 里的调用换成：

```tsx
      const projectId = await importAndTranslate(article, { web, agent: useAgent ? choice : null });
      if (useAgent) saveAgentChoice(choice);
```

`<>…</>`（非 cookie 分支）整个换成：

```tsx
          <>
            <p className="text-sm font-medium text-text-primary">导入后怎么翻</p>
            <div className="mt-2 space-y-1">
              <Check checked={web} onChange={setWeb} label="网页版" note="网站自己的翻译流程" disabled={busy} />
              <Check checked={useAgent} onChange={setUseAgent} label="Agent" note="在服务器上跑，关掉页面也不会停" disabled={busy}>
                {useAgent && (
                  <div className="mt-2.5">
                    <AgentChoiceFields options={ARTICLE_HARNESSES.map(item => item.id)} value={choice} onChange={setChoice} disabled={busy} />
                  </div>
                )}
              </Check>
            </div>
            <Button className="mt-4 w-full" onClick={start} disabled={busy}>
              {busy ? <><Loader2 className="animate-spin" /> 导入中…</> : web || useAgent ? '导入并翻译' : '导入'}
            </Button>
          </>
```

文件末尾加：

```tsx
function Check({ checked, onChange, label, note, disabled, children }: {
  checked: boolean; onChange: (value: boolean) => void; label: string; note: string; disabled: boolean; children?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg px-2 py-2">
      <label className="flex cursor-pointer items-start gap-2.5">
        <input type="checkbox" checked={checked} disabled={disabled} onChange={event => onChange(event.target.checked)}
          className="mt-1 h-4 w-4 accent-[var(--color-primary-500)]" />
        <span className="text-sm text-text-primary">
          {label}
          <span className="block text-xs text-text-muted">{note}</span>
        </span>
      </label>
      {children && <div className="pl-[26px]">{children}</div>}
    </div>
  );
}
```

（顶部 `import` 加 `import type { ReactNode } from 'react';` 并把 `React.ReactNode` 换成 `ReactNode`，按 lint 要求二选一。）
同时删掉那句「付费文章 Claude 通常不肯全文翻译，只给导读」——它在被替换的 JSX 里，替换后已不存在；用 `rg "不肯全文" src/features/articles` 确认没有残留
（「这是付费文章，要先填订阅 cookie」是下载用的，保留）。

删除 `components/ArticleAgentChoice.tsx`。

- [ ] **Step 5: 全量前端检查**

Run: `npm test && npx tsc -b && npm run lint`
Expected: 全部通过

- [ ] **Step 6: 提交**

```bash
git add src/features/articles/lib/importFlow.ts src/features/articles/components/ArticlePreview.tsx src/features/articles/articles.test.tsx
git rm src/features/articles/components/ArticleAgentChoice.tsx
git commit -m "feat(articles): import with two checkboxes and the shared agent + model picker"
```

---

### Task 14: 端到端与视觉验收

**Files:** `tests/e2e/article-reading.spec.ts`

- [ ] **Step 1: 改 e2e**

- `{ name: '译本 1正文' }` → `{ name: '主译本正文' }`
- `'译本 1：从这里继续阅读 — First sentence.'` → `'主译本：从这里继续阅读 — First sentence.'`
- 两处 `'编辑：译本 1：Second sentence.'` / `'译本 1：Second sentence.'` → `'编辑：主译本：Second sentence.'` / `'主译本：Second sentence.'`
- `await page.getByRole('button', { name: '继续阅读', exact: true }).click();` 之前加
  `await page.getByRole('button', { name: '阅读标记', exact: true }).click();`；
  第一处只断言可见的那行改成 `await expect(page.getByRole('button', { name: '阅读标记', exact: true })).toBeVisible();`
- mock 的 `project` 加 `primary: 'reading', primary_target: null`

- [ ] **Step 2:** `npx playwright test tests/e2e/article-reading.spec.ts`（本机 Playwright 的 `executablePath` 指向 `%LOCALAPPDATA%/ms-playwright/chromium-1234/chrome-win64/chrome.exe`，见 `playwright.config`）→ 通过

- [ ] **Step 3: 截图测试** `tests/e2e/workbench-visual.spec.ts`（提交；只断言结构，图片给人看）

```ts
import { expect, test, type Page } from '@playwright/test';

const status = { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null };
const rows = [
  { key: 'section:s1', kind: 'section', section_id: 's1', paragraph_id: null, source: 'The base die moves to logic',
    web: '基底裸片改用逻辑工艺', alt: { 'v--codex': '基底裸片转向逻辑工艺' } },
  { key: 's1/p0', kind: 'p', section_id: 's1', paragraph_id: 'p0',
    source: 'HBM4 moves the base die from a DRAM process to a logic process, and that single change reshapes the cost stack in three ways.',
    web: 'HBM4 把基底裸片从 DRAM 工艺换成逻辑工艺，这一处改动从三个方面重塑了成本结构。',
    alt: { 'v--codex': 'HBM4 将基底裸片由 DRAM 制程改为逻辑制程，仅此一项变化便从三方面重塑成本结构。' } },
];
const codex = { id: 'v--codex', kind: 'claude', label: 'Codex', title_translation: null, progress: { total: 2, approved: 0 }, status,
  import: { run_id: 'r0', agent: 'codex', model: 'gpt-5.5', aligned: 2, unaligned: 0, merged_blocks: 0, imported_at: '2026-10-28T10:00:00' } };
const project = { id: 'v', title: 'HBM4 Cost Structure', title_translation: 'HBM4 的成本结构', original_url: null, created_at: '',
  progress: { total: 2, approved: 0 }, status, primary_target: null };

const CASES = {
  'web-primary-codex-waiting': { project: { ...project, claude_run_id: 'r1', primary: 'v' }, variants: [codex],
    run: { id: 'r1', skill: 'four-step-translate', title: 't', status: 'idle', awaiting_reply: true, auto_reply_at: 1_793_250_000,
      created_at: 0, updated_at: 0, session_id: 's', error: null, harness: 'codex' } },
  'codex-primary-retranslating': { project: { ...project, claude_run_id: 'r2', primary: 'v--codex' }, variants: [codex],
    run: { id: 'r2', skill: 'four-step-translate', title: 't', status: 'running', model: 'gpt-5.5-codex',
      created_at: 0, updated_at: 0, session_id: 's', error: null, harness: 'codex' } },
  'web-only': { project: { ...project, claude_run_id: null, primary: 'v' }, variants: [], run: null },
} as const;

async function open(page: Page, name: keyof typeof CASES) {
  const item = CASES[name];
  await page.route('**/api/substack/**', route => route.fulfill({ json: { articles: [], total: 0, added: 0, next_offset: null } }));
  await page.route('**/api/projects/v/workbench', route => route.fulfill({ json: { project: item.project, variants: item.variants, rows, reading_mark: null } }));
  await page.route('**/api/skills/runs/*', route => route.fulfill({ json: item.run }));
  await page.route('**/api/skills/models/*', route => route.fulfill({ json: { models: [], default_model: 'gpt-5.5', source: 'cache', warning: null } }));
  await page.goto('/articles/v');
  await expect(page.getByRole('article', { name: '主译本正文' })).toBeVisible();
}

for (const [width, height] of [[1440, 900], [390, 844]] as const) {
  for (const name of Object.keys(CASES) as (keyof typeof CASES)[]) {
    test(`workbench ${name} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await open(page, name);
      expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
      await expect(page.getByText('在等你确认', { exact: false })).toHaveCount(0); // 旧横幅文案不该再出现
      await page.screenshot({ path: `test-results/workbench-${name}-${width}.png`, fullPage: false });
    });
  }
}
```

Run: `npx playwright test tests/e2e/workbench-visual.spec.ts` → 6 passed，截图在 `web/frontend/test-results/`。

打开这 6 张图，对照设计文档第 5、6 节逐条检查：

- 正文上方只有顶栏和栏头两层；三栏栏头一样高；
- 主译本栏有梅红细线和浅暖底，状态都在状态行，没有横幅；
- 中文是宋体、英文是衬线体；
- 弹框是单选列表、Agent 是卡片；
- 手机上对照栏是下拉，没有横向滚动条（`document.documentElement.scrollWidth <= innerWidth`）。

发现问题回到对应 Task 修，修完重截。

- [ ] **Step 4: 提交**

```bash
git add tests/e2e/article-reading.spec.ts tests/e2e/workbench-visual.spec.ts
git commit -m "test(e2e): workbench reading flow and visual states"
```

---

### Task 15: 收尾

- [ ] **Step 0: 改掉注释里的旧叫法**（其中两处描述的行为已经变了）

| 文件:行 | 改成 |
|---|---|
| `src/features/articles/api.ts:36` | `* 后台四步法；模型版传 model 并自动采用术语建议，不打断用户。` |
| `src/features/articles/components/ChangesDrawer.tsx:13` | `/** 版本名，例如「网页版」「Codex」 */` |
| `src/features/articles/lib/tracks.ts:4` | `/** 以前「换个模型再翻一版」的模型（llm_providers.yaml 里的别名），只用来给模型版继续翻译。label 也是孪生项目 id 后缀。 */` |
| `src/features/articles/lib/tracks.ts:54` | `/** 已导入文章的翻译进度（只看主译本，后端算好）；没导入时为 null。 */` |
| `src/features/articles/types.ts:31` | `/** 网页版以外的一版：同源孪生项目。kind=model 是以前换模型再翻的，kind=claude 是从 Agent 任务导入的。 */` |
| `src/features/articles/types.ts:55` | `/** 网页版（主项目）的译文 */` |
| `src/features/articles/types.ts:57` | `/** 其余各版的译文，键是孪生项目 id */` |
| `src/features/substack/api.ts:6` | 句末「网页版和译本 2 取进度高的那一版」改为「只看主译本那一版」 |

`importFlow.ts:8` 的注释在 Task 13 已经整个换掉。

- [ ] **Step 1:** `rg -n "译本 1|译本 2|Antigravity|不肯全文|付费文章也肯" src/features/articles src/features/substack src/features/skills --glob '!*.test.*'` → 只剩 `skills/harness.ts` 里说明内部 id 的那行注释（导入时填 cookie 的「这是付费文章，要先填订阅 cookie」要保留，它和 Agent 无关）
- [ ] **Step 2:** `npm test && npx tsc -b && npm run lint && npm run build` → 全部通过
- [ ] **Step 3:** 后端一起：在 worktree 根目录 `python -m pytest tests/unit -q -x --ignore=tests/unit/regression` → 与基线相比没有新增失败
