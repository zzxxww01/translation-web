import payload from '../../../../config/editing_options.json';
import morePayload from '../../../../config/post_more_options.json';

export const EDITING_OPTION_VERSION = payload.version;
export const EDITING_OPTIONS = payload.options;
export const EDITING_OPTIONS_BY_ID = Object.fromEntries(EDITING_OPTIONS.map(item => [item.id, item]));
export function getEditingInstruction(id: string): string {
  return EDITING_OPTIONS_BY_ID[id]?.instruction ?? '';
}

/** 帖子翻译「更多…」里的优化指令（按指令原文发，不是 option_id）；Muse 的 optimize-draft 用同一份 */
export const MORE_POST_OPTIONS = morePayload.options;
