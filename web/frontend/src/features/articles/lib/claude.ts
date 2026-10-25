import { fileUrl, skillsApi, startRun } from '@/features/skills/api';
import type { RunFile, RunMeta } from '@/features/skills/types';
import { articlesApi } from '../api';

export const CLAUDE_SKILL = 'four-step-translate';
const CLAUDE_MESSAGE =
  '精翻附件里的这篇文章。输出目录放在当前目录下的 output/ 里（不用 SKILL.md 配置里的 output_root）。';

export class NoClaudeOutput extends Error {
  constructor() {
    super('Claude 这次没有产出 zh.md（付费文章它通常不肯全文翻译，会改写成导读）');
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

/** 把原文交给 Claude，并记下这篇文章对应的任务。 */
export async function startClaudeTrack(projectId: string): Promise<RunMeta> {
  const html = await articlesApi.sourceHtml(projectId);
  const run = await startRun({ skill: CLAUDE_SKILL, message: CLAUDE_MESSAGE, files: [html] });
  await articlesApi.setClaudeRun(projectId, run.id);
  return run;
}

async function readText(runId: string, path: string): Promise<string> {
  const response = await fetch(fileUrl(runId, path));
  if (!response.ok) throw new Error(`读不到 ${path}（${response.status}）`);
  return response.text();
}

/** 从 Claude 任务取回 zh.md / en.md，对齐后存成 `--claude` 译本。 */
export async function importClaudeTrack(projectId: string, runId: string) {
  const outputs = findClaudeOutputs(await skillsApi.files(runId));
  if (!outputs) throw new NoClaudeOutput();
  const [zh, en] = await Promise.all([readText(runId, outputs.zh), readText(runId, outputs.en)]);
  return articlesApi.importClaude(projectId, { run_id: runId, zh_markdown: zh, en_markdown: en });
}
