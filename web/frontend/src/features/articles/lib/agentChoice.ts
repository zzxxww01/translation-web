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
