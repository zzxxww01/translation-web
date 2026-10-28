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
