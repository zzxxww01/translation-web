import { apiClient, ApiErrorWrapper } from '@/shared/api/client';
import type { Project } from '@/shared/types';

/**
 * not_imported 没导入；imported 已导入还没翻；awaiting_terms 翻译在等你确认术语；
 * translating 翻译中；partial 翻了一部分停下了；translated 已译完
 */
export type ArticleStatus =
  | 'not_imported'
  | 'imported'
  | 'awaiting_terms'
  | 'translating'
  | 'partial'
  | 'translated';

export type ArticleFilter = 'all' | 'not_imported' | 'imported';

export interface SubstackArticle {
  title: string;
  subtitle: string;
  slug: string;
  url: string;
  post_date: string;
  is_paid: boolean;
  cover_image: string | null;
  wordcount: number | null;
  /** 自动生成的中文标题和一句话摘要；还没生成时为空字符串 */
  zh_title: string;
  zh_summary: string;
  /** 已导入时为对应项目 ID */
  project_id: string | null;
  status: ArticleStatus;
  /** 已翻段落的百分比 */
  progress: number;
}

export interface SubstackArticlePage {
  articles: SubstackArticle[];
  next_offset: number | null;
  /** 符合当前搜索和筛选的总篇数 */
  total: number;
  pending_digests: number;
  /** 后台正在生成中文标题和摘要 */
  digesting: boolean;
}

export interface SubstackSyncResult {
  added: number;
  total: number;
}

export interface SubstackImportResult {
  project: Project;
  already_imported: boolean;
}

export interface SubstackCookieStatus {
  configured: boolean;
  domain: string;
}

export const ARTICLES_PAGE_SIZE = 24;

export const substackApi = {
  // 平时读服务器上存的清单，很快；只有第一次打开要把全部清单拉下来，十几秒
  listArticles: (offset: number, search: string, filter: ArticleFilter = 'all') =>
    apiClient.get<SubstackArticlePage>('/substack/articles', {
      params: {
        offset,
        limit: ARTICLES_PAGE_SIZE,
        ...(search ? { search } : {}),
        ...(filter !== 'all' ? { filter } : {}),
      },
      timeout: 120_000,
    }),

  /** 去 Substack 看有没有新文章；full 为 true 时把全部清单重新拉一遍 */
  syncArticles: (full = false) =>
    apiClient.post<SubstackSyncResult>('/substack/articles/sync', undefined, {
      params: full ? { full: true } : {},
      retry: false,
      timeout: 120_000,
    }),

  // 导入要下载整页 HTML 再建项目，比普通请求慢；失败不自动重试，避免重复下载
  importArticle: (url: string, name?: string) =>
    apiClient.post<SubstackImportResult>(
      '/substack/import',
      { url, ...(name ? { name } : {}) },
      { retry: false, timeout: 120_000 },
    ),

  getCookieStatus: () => apiClient.get<SubstackCookieStatus>('/substack/cookie'),

  saveCookie: (cookie: string) =>
    apiClient.put<SubstackCookieStatus>('/substack/cookie', { cookie }, { retry: false }),
};

/** 这些错误靠重新填写订阅 cookie 就能解决，界面上直接弹出 cookie 输入框。 */
const COOKIE_ERROR_CODES = new Set(['COOKIE_MISSING', 'COOKIE_EXPIRED']);

export function substackErrorCode(error: unknown): string | undefined {
  if (!(error instanceof ApiErrorWrapper)) return undefined;
  const data = error.data as { error_code?: unknown } | undefined;
  return typeof data?.error_code === 'string' ? data.error_code : undefined;
}

export function isCookieError(error: unknown): boolean {
  return COOKIE_ERROR_CODES.has(substackErrorCode(error) ?? '');
}

export function errorText(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}
