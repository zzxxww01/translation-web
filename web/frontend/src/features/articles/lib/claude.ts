import { AUTO_REPLY_MINUTES, fileUrl, skillsApi, startRun } from '@/features/skills/api';
import type { RunFile, RunMeta } from '@/features/skills/types';
import { ApiErrorWrapper } from '@/shared/api/client';
import { articlesApi } from '../api';
import type { AgentChoice } from './agentChoice';

export const CLAUDE_SKILL = 'four-step-translate';
const CLAUDE_MESSAGE =
  '精翻附件里的这篇文章。输出目录放在当前目录下的 output/ 里（不用 SKILL.md 配置里的 output_root）。';

export class NoClaudeOutput extends Error {
  constructor() {
    super('没找到同一目录下的 zh.md 和 en.md');
    this.name = 'NoClaudeOutput';
  }
}

/** 任务目录里最新的 zh.md 和同一目录的 en.md；没有就返回 null。 */
export function findClaudeOutputs(files: RunFile[]): { zh: string; en: string } | null {
  const zhFiles = files.filter(file => file.path === 'zh.md' || file.path.endsWith('/zh.md'));
  zhFiles.sort((a, b) => b.mtime - a.mtime);
  for (const zh of zhFiles) {
    const dir = zh.path.slice(0, zh.path.length - 'zh.md'.length);
    const en = files.find(file => file.path === `${dir}en.md`);
    if (en) return { zh: zh.path, en: en.path };
  }
  return null;
}

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

/** 后端 409：Agent 的英文稿和下载的原文对不上（多半不是这篇），可以「仍然导入」。 */
export class AlignmentTooLow extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AlignmentTooLow';
  }
}

async function readText(runId: string, path: string): Promise<string> {
  const response = await fetch(fileUrl(runId, path));
  if (!response.ok) throw new Error(`读不到 ${path}（${response.status}）`);
  return response.text();
}

function isAlignmentLow(error: unknown): error is ApiErrorWrapper {
  if (!(error instanceof ApiErrorWrapper) || error.status !== 409) return false;
  const data = error.data;
  return Boolean(data && typeof data === 'object' && (data as { error_code?: unknown }).error_code === 'ALIGNMENT_LOW');
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
    if (isAlignmentLow(error)) throw new AlignmentTooLow(error.message);
    throw error;
  }
}
