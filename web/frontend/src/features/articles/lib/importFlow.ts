import { toast } from 'sonner';
import { substackApi, type SubstackArticle } from '@/features/substack/api';
import { isUnauthorized } from '@/features/skills/hooks';
import { articlesApi } from '../api';
import { startClaudeTrack } from './claude';
import type { SECOND_MODELS } from './tracks';

export type SecondChoice = 'model' | 'claude' | 'codex' | 'none';

/** 导入 → 启动网页版 → 启动译本 2。译本 2 失败不挡住进工作台，只提示。返回主项目 id。 */
export async function importAndTranslate(
  article: Pick<SubstackArticle, 'url'>,
  second: SecondChoice,
  model: (typeof SECOND_MODELS)[number],
  notify: (message: string) => void = message => toast.warning(message),
): Promise<string> {
  const imported = await substackApi.importArticle(article.url);
  const projectId = imported.project.id;
  if (!imported.already_imported) {
    try {
      await articlesApi.startWorkflow(projectId);
    } catch (error) {
      notify(`网页版没能开始：${error instanceof Error ? error.message : error}`);
    }
  }
  try {
    if (second === 'model') {
      const { variant_id } = await articlesApi.createModelVariant(projectId, model.model, model.label);
      await articlesApi.startWorkflow(variant_id, { model: model.model, autoAcceptTerms: true });
    } else if (second === 'claude' || second === 'codex') {
      await startClaudeTrack(projectId, second);
    }
  } catch (error) {
    notify(isUnauthorized(error)
      ? '要先在 Agent 页登录一次：登录后在工作台「更多」里重新交给 Claude / Codex'
      : `译本 2 没能开始：${error instanceof Error ? error.message : error}`);
  }
  return projectId;
}
