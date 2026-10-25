import { toast } from 'sonner';
import { substackApi, type SubstackArticle } from '@/features/substack/api';
import type { Harness } from '@/features/skills/harness';
import { isUnauthorized } from '@/features/skills/hooks';
import { articlesApi } from '../api';
import { startClaudeTrack } from './claude';

/** 导入后翻哪几版：只导入 / 只翻网页版（译本 1）/ 只用 Agent（译本 2）/ 两个都翻 */
export type ImportPlan = 'import' | 'web' | 'agent' | 'both';

export const runsWeb = (plan: ImportPlan) => plan === 'web' || plan === 'both';
export const runsAgent = (plan: ImportPlan) => plan === 'agent' || plan === 'both';

/** 导入 → 按计划启动网页版和 Agent。某一路没能开始不挡住进工作台，只提示。返回主项目 id。 */
export async function importAndTranslate(
  article: Pick<SubstackArticle, 'url'>,
  plan: ImportPlan,
  harness: Harness,
  notify: (message: string) => void = message => toast.warning(message),
): Promise<string> {
  const imported = await substackApi.importArticle(article.url);
  const projectId = imported.project.id;
  if (imported.already_imported) return projectId;
  if (runsWeb(plan)) {
    try {
      await articlesApi.startWorkflow(projectId);
    } catch (error) {
      notify(`网页版没能开始：${error instanceof Error ? error.message : error}`);
    }
  }
  if (runsAgent(plan)) {
    try {
      await startClaudeTrack(projectId, harness);
    } catch (error) {
      notify(isUnauthorized(error)
        ? '要先在 Agent 页登录一次：登录后在工作台里重新交给 Codex / Claude'
        : `Agent 没能开始：${error instanceof Error ? error.message : error}`);
    }
  }
  return projectId;
}
