import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  type InfiniteData,
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { KeyRound, Loader2, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button-extended';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { DEFAULT_TRANSLATION_METHOD } from '@/shared/constants';
import { documentApi } from '../document/api';
import {
  type ArticleFilter,
  errorText,
  isCookieError,
  substackApi,
  type SubstackArticle,
  type SubstackArticlePage,
} from './api';
import { ArticleRow, type ImportMode } from './components/ArticleRow';
import { CookieForm } from './components/CookieForm';

const ARTICLES_KEY = 'substack-articles';
const COOKIE_KEY = ['substack-cookie'];
const LAST_VISIT_KEY = 'substack-library:last-visit';
// 后台在生成中文、或有文章正在翻译时，隔这么久刷新一次列表
const LIVE_REFRESH_MS = 5000;

const FILTERS: { value: ArticleFilter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'not_imported', label: '没导入' },
  { value: 'imported', label: '已导入' },
];

interface CookiePrompt {
  reason?: string;
  /** 填好 cookie 后自动重试的那次导入 */
  retry?: { article: SubstackArticle; mode: ImportMode };
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/** 上次打开文章库的时间（第一次打开为 null）；读完就记下这次的时间。 */
function useLastVisit(): number | null {
  const [previous] = useState(() => {
    try {
      const value = Number(localStorage.getItem(LAST_VISIT_KEY));
      return Number.isFinite(value) && value > 0 ? value : null;
    } catch {
      return null; // 隐私模式等读不了本地存储
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(LAST_VISIT_KEY, String(Date.now()));
    } catch {
      // 记不下来只是下次不显示「新」标记
    }
  }, []);
  return previous;
}

function needsLiveRefresh(data: InfiniteData<SubstackArticlePage> | undefined): boolean {
  return Boolean(
    data?.pages.some(
      page =>
        page.digesting ||
        page.articles.some(a => a.status === 'translating' || a.status === 'awaiting_terms')
    )
  );
}

export function SubstackFeature() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState('');
  const search = useDebouncedValue(searchInput.trim(), 400);
  const [filter, setFilter] = useState<ArticleFilter>('all');
  const [busy, setBusy] = useState<Record<string, ImportMode>>({});
  const [cookiePrompt, setCookiePrompt] = useState<CookiePrompt | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const lastVisit = useLastVisit();
  const sentinelRef = useRef<HTMLDivElement>(null);
  const checkedForNewRef = useRef(false);

  const cookieStatus = useQuery({ queryKey: COOKIE_KEY, queryFn: substackApi.getCookieStatus });

  const articles = useInfiniteQuery({
    queryKey: [ARTICLES_KEY, search, filter],
    queryFn: ({ pageParam }) => substackApi.listArticles(pageParam, search, filter),
    initialPageParam: 0,
    getNextPageParam: last => last.next_offset ?? undefined,
    refetchInterval: query => (needsLiveRefresh(query.state.data) ? LIVE_REFRESH_MS : false),
  });
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = articles;
  const pages = articles.data?.pages;
  const items = pages?.flatMap(page => page.articles) ?? [];
  const firstPage = pages?.[0];

  const reloadArticles = useCallback(
    () => queryClient.invalidateQueries({ queryKey: [ARTICLES_KEY] }),
    [queryClient]
  );

  // 清单先秒开（读服务器存的那份），再去 Substack 看一眼有没有新文章
  const loaded = articles.isSuccess;
  useEffect(() => {
    if (!loaded || checkedForNewRef.current) return;
    checkedForNewRef.current = true;
    substackApi
      .syncArticles()
      .then(({ added }) => {
        if (added > 0) {
          toast.info(`有 ${added} 篇新文章`);
          void reloadArticles();
        }
      })
      .catch(() => {
        // 看不了新文章不影响浏览已存的清单；想重试可以点「刷新清单」
      });
  }, [loaded, reloadArticles]);

  // 滚到列表底部时自动加载更早的文章
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasNextPage) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting) && !isFetchingNextPage) {
        void fetchNextPage();
      }
    }, { rootMargin: '400px' });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  const openProject = useCallback((projectId: string) => navigate(`/document/${projectId}`), [navigate]);

  const markImported = useCallback((slug: string, projectId: string) => {
    queryClient.setQueriesData<InfiniteData<SubstackArticlePage>>({ queryKey: [ARTICLES_KEY] }, data =>
      data && {
        ...data,
        pages: data.pages.map(page => ({
          ...page,
          articles: page.articles.map(a =>
            a.slug === slug ? { ...a, project_id: projectId, status: 'imported' as const, progress: 0 } : a
          ),
        })),
      }
    );
    void queryClient.invalidateQueries({ queryKey: ['projects'] });
  }, [queryClient]);

  /** 开始翻译并进入项目页：术语确认会在项目页弹出，不会错过。成功返回 true。 */
  const startTranslation = useCallback(async (projectId: string) => {
    // 与项目页「全文一键翻译」的默认设置一致；翻译在服务器后台进行
    await documentApi.startLongformWorkflow(projectId, DEFAULT_TRANSLATION_METHOD, undefined, undefined, {
      model_scope: 'all',
      efficiency: { compact_review: false },
    });
    openProject(projectId);
  }, [openProject]);

  const setBusyFor = useCallback((slug: string, mode: ImportMode | null) =>
    setBusy(prev => {
      const next = { ...prev };
      if (mode) next[slug] = mode;
      else delete next[slug];
      return next;
    }), []);

  const runImport = useCallback(async (article: SubstackArticle, mode: ImportMode) => {
    setBusyFor(article.slug, mode);
    try {
      const { project, already_imported } = await substackApi.importArticle(article.url);
      markImported(article.slug, project.id);
      const open = { label: '打开', onClick: () => openProject(project.id) };

      if (already_imported) {
        toast.info('这篇之前已经导入过了', { action: open });
      } else if (mode === 'translate') {
        try {
          await startTranslation(project.id);
        } catch (error) {
          toast.error(`已导入，但启动翻译失败：${errorText(error, '请打开项目手动开始')}`, { action: open });
        }
      } else {
        toast.success(`已导入：${project.title}`, { action: open });
      }
    } catch (error) {
      if (isCookieError(error)) {
        setCookiePrompt({ reason: errorText(error, '需要订阅 cookie'), retry: { article, mode } });
      } else {
        toast.error(errorText(error, '导入失败'));
      }
    } finally {
      setBusyFor(article.slug, null);
    }
  }, [markImported, openProject, setBusyFor, startTranslation]);

  const runTranslate = useCallback(async (article: SubstackArticle) => {
    const projectId = article.project_id;
    if (!projectId) return;
    setBusyFor(article.slug, 'translate');
    try {
      await startTranslation(projectId);
    } catch (error) {
      toast.error(`启动翻译失败：${errorText(error, '请打开项目手动开始')}`, {
        action: { label: '打开', onClick: () => openProject(projectId) },
      });
    } finally {
      setBusyFor(article.slug, null);
    }
  }, [openProject, setBusyFor, startTranslation]);

  const handleCookieSaved = () => {
    const retry = cookiePrompt?.retry;
    setCookiePrompt(null);
    void queryClient.invalidateQueries({ queryKey: COOKIE_KEY });
    if (retry) void runImport(retry.article, retry.mode);
  };

  const refreshList = async () => {
    setIsRefreshing(true);
    try {
      const { added } = await substackApi.syncArticles(true);
      toast.success(added > 0 ? `清单已更新，新增 ${added} 篇` : '清单已是最新');
      await reloadArticles();
    } catch (error) {
      toast.error(errorText(error, '刷新清单失败'));
    } finally {
      setIsRefreshing(false);
    }
  };

  const isNew = (article: SubstackArticle) =>
    lastVisit !== null && Date.parse(article.post_date) > lastVisit;

  const cookieConfigured = cookieStatus.data?.configured;

  return (
    <div className="flex h-full min-w-0 overflow-auto">
      <div className="mx-auto w-full min-w-0 max-w-3xl px-5 pb-12 pt-8 sm:px-8 sm:pt-10">
        <PageHeader
          className="mb-6"
          title="SemiAnalysis 文章"
          description="按发布时间列出全部文章。点「导入」下载全文建成项目；点「导入并翻译」会直接进入项目，先确认术语再开始翻译。"
          actions={
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                isLoading={isRefreshing}
                leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
                onClick={() => void refreshList()}
              >
                刷新清单
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                leftIcon={<KeyRound className="h-3.5 w-3.5" />}
                onClick={() => setCookiePrompt(prev => (prev ? null : {}))}
              >
                {cookieStatus.isLoading ? '订阅 cookie' : cookieConfigured ? '订阅 cookie 已配置' : '填写订阅 cookie'}
              </Button>
            </div>
          }
        />

        {cookiePrompt && (
          <div className="mb-5">
            <CookieForm
              reason={cookiePrompt.reason}
              domain={cookieStatus.data?.domain}
              onSaved={handleCookieSaved}
              onCancel={() => setCookiePrompt(null)}
            />
          </div>
        )}

        <div className="relative mb-3">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <Input
            aria-label="搜索文章"
            placeholder="搜索标题或摘要，中英文都行，例如 HBM、台积电"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-2">
          <div className="inline-flex rounded-lg border border-border bg-bg-tertiary p-0.5" role="group" aria-label="筛选">
            {FILTERS.map(option => (
              <button
                key={option.value}
                type="button"
                aria-pressed={filter === option.value}
                onClick={() => setFilter(option.value)}
                className={cn(
                  'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                  filter === option.value
                    ? 'bg-white text-text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary'
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          {firstPage && <span className="text-xs text-text-muted">共 {firstPage.total} 篇</span>}
          {firstPage?.digesting && firstPage.pending_digests > 0 && (
            <span className="inline-flex items-center gap-1 text-xs text-text-muted">
              <Loader2 className="h-3 w-3 animate-spin" />
              正在生成中文标题和摘要，还剩 {firstPage.pending_digests} 篇
            </span>
          )}
        </div>

        {articles.isLoading ? (
          <div className="flex flex-col items-center justify-center gap-1 py-16 text-sm text-text-muted">
            <span className="inline-flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> 正在读取文章清单…
            </span>
            <span className="text-xs">第一次打开要把全部文章清单拉下来，大约十几秒</span>
          </div>
        ) : articles.isError ? (
          <div className="space-y-3 py-16 text-center text-sm text-text-muted">
            <p>{errorText(articles.error, '读取文章列表失败')}</p>
            <Button type="button" size="sm" variant="outline" onClick={() => void articles.refetch()}>
              重试
            </Button>
          </div>
        ) : items.length === 0 ? (
          <p className="py-16 text-center text-sm text-text-muted">
            {search
              ? `没有找到和「${search}」相关的文章`
              : filter === 'imported'
                ? '还没有导入过文章'
                : filter === 'not_imported'
                  ? '文章都导入过了'
                  : '还没有文章'}
          </p>
        ) : (
          <>
            <ul>
              {items.map(article => (
                <ArticleRow
                  key={article.slug}
                  article={article}
                  busyMode={busy[article.slug]}
                  isNew={isNew(article)}
                  onImport={runImport}
                  onTranslate={runTranslate}
                  onOpen={openProject}
                />
              ))}
            </ul>
            <div ref={sentinelRef} className="flex justify-center py-6">
              {hasNextPage ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  isLoading={isFetchingNextPage}
                  onClick={() => void fetchNextPage()}
                >
                  加载更早的文章
                </Button>
              ) : (
                <span className="text-xs text-text-muted">已经到底了，共 {items.length} 篇</span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
