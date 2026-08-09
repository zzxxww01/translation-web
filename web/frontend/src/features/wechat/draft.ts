import type { WechatDraft, WechatImageMode } from './types';

export const WECHAT_DRAFT_STORAGE_KEY = 'translation_agent_wechat_draft';

export const EMPTY_WECHAT_DRAFT: WechatDraft = {
  markdown: '',
  selectedTheme: 'default',
  imageMode: 'keep',
};

function isImageMode(value: unknown): value is WechatImageMode {
  return value === 'keep' || value === 'upload' || value === 'base64';
}

export function parseWechatDraft(raw: string | null): WechatDraft {
  if (!raw) return EMPTY_WECHAT_DRAFT;

  try {
    const value = JSON.parse(raw) as Partial<WechatDraft>;
    return {
      markdown: typeof value.markdown === 'string' ? value.markdown : '',
      selectedTheme:
        typeof value.selectedTheme === 'string' && value.selectedTheme
          ? value.selectedTheme
          : 'default',
      imageMode: isImageMode(value.imageMode) ? value.imageMode : 'keep',
    };
  } catch {
    return EMPTY_WECHAT_DRAFT;
  }
}

export function loadWechatDraft(): WechatDraft {
  if (typeof window === 'undefined') return EMPTY_WECHAT_DRAFT;
  try {
    return parseWechatDraft(window.localStorage.getItem(WECHAT_DRAFT_STORAGE_KEY));
  } catch {
    return EMPTY_WECHAT_DRAFT;
  }
}

export function saveWechatDraft(draft: WechatDraft): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(WECHAT_DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Safari 隐私模式、存储配额耗尽等情况下仍允许继续排版。
  }
}
