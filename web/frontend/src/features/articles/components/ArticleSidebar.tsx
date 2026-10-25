import { useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { substackApi, type ArticleFilter, type SubstackArticle } from '@/features/substack/api';
import { useLibrary, useProjects } from '../hooks';
import { statusText } from '../lib/tracks';

const FILTERS: { id: ArticleFilter; label: string }[] = [
  { id: 'all', label: '全部' },
  { id: 'not_imported', label: '未导入' },
  { id: 'imported', label: '已导入' },
];

const shortDate = new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' });

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

interface ArticleSidebarProps {
  selectedSlug: string | null;
  selectedProjectId: string | null;
  onSelectArticle: (article: SubstackArticle) => void;
  onSelectProject: (projectId: string) => void;
}

/** 文章库的文章和自己的项目放在一个列表里，用筛选切换。 */
export function ArticleSidebar({ selectedSlug, selectedProjectId, onSelectArticle, onSelectProject }: ArticleSidebarProps) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<ArticleFilter>('all');
  const [input, setInput] = useState('');
  const search = useDebounced(input.trim(), 300);
  const library = useLibrary(filter, search);
  const projects = useProjects(filter === 'imported');
  const [syncing, setSyncing] = useState(false);
  const sentinel = useRef<HTMLLIElement>(null);

  const articles = useMemo(() => library.data?.pages.flatMap(page => page.articles) ?? [], [library.data]);
  const total = library.data?.pages[0]?.total ?? 0;
  // 「已导入」里补上不在文章库里的项目（手动上传的）
  const otherProjects = useMemo(() => {
    if (filter !== 'imported' || !projects.data || library.hasNextPage) return [];
    const linked = new Set(articles.map(article => article.project_id).filter(Boolean));
    const keyword = search.toLowerCase();
    return projects.data.filter(project => !linked.has(project.id) && (!keyword || project.title.toLowerCase().includes(keyword)));
  }, [filter, projects.data, articles, library.hasNextPage, search]);

  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const observer = new IntersectionObserver(entries => {
      if (entries[0]?.isIntersecting && library.hasNextPage && !library.isFetchingNextPage) void library.fetchNextPage();
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [library]);

  const sync = async () => {
    setSyncing(true);
    try {
      const result = await substackApi.syncArticles();
      toast.success(result.added ? `新增 ${result.added} 篇` : '没有新文章');
      await queryClient.invalidateQueries({ queryKey: ['articles', 'library'] });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '同步失败');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="space-y-2 border-b border-border-subtle px-3 pb-3 pt-4">
        <div className="flex items-center gap-2">
          <h2 className="flex-1 text-sm font-medium text-text-secondary">文章 <span className="text-text-muted">{total || ''}</span></h2>
          <button type="button" onClick={sync} disabled={syncing} title="去 Substack 看有没有新文章" className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary disabled:opacity-50">
            <RefreshCw className={cn('h-3.5 w-3.5', syncing && 'animate-spin')} />
          </button>
        </div>
        <label className="flex items-center gap-2 rounded-md border border-border-subtle bg-white px-2.5 py-1.5 focus-within:border-primary-300">
          <Search className="h-3.5 w-3.5 text-text-muted" />
          <input value={input} onChange={event => setInput(event.target.value)} placeholder="搜索标题" aria-label="搜索文章" className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-text-disabled" />
        </label>
        <div className="flex gap-1" role="group" aria-label="筛选文章">
          {FILTERS.map(item => (
            <button
              key={item.id}
              type="button"
              aria-pressed={filter === item.id}
              onClick={() => setFilter(item.id)}
              className={cn('rounded-md px-2.5 py-1 text-xs transition-colors', filter === item.id ? 'bg-primary-50 font-medium text-primary-700' : 'text-text-muted hover:bg-bg-hover hover:text-text-primary')}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <ul className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {library.isPending && <li className="px-3 py-6 text-center text-sm text-text-muted">读取文章库…（第一次要把清单拉下来，十几秒）</li>}
        {library.error && <li className="px-3 py-6 text-center text-sm text-error">文章库读不到：{library.error.message}</li>}
        {!library.isPending && !articles.length && !otherProjects.length && (
          <li className="px-3 py-6 text-center text-sm text-text-muted">没有符合的文章</li>
        )}
        {articles.map(article => {
          const selected = article.project_id ? article.project_id === selectedProjectId : article.slug === selectedSlug;
          const status = statusText(article.status, article.progress);
          return (
            <li key={article.url}>
              <button
                type="button"
                onClick={() => (article.project_id ? onSelectProject(article.project_id) : onSelectArticle(article))}
                className={cn('w-full rounded-md px-3 py-2.5 text-left transition-colors', selected ? 'bg-primary-50' : 'hover:bg-bg-hover')}
              >
                <span className="line-clamp-2 text-sm leading-snug text-text-primary">{article.zh_title || article.title}</span>
                {article.zh_title && <span className="mt-0.5 block truncate text-xs text-text-muted">{article.title}</span>}
                <span className="mt-1 flex items-center gap-2 text-[11px] text-text-muted">
                  <span>{Number.isFinite(Date.parse(article.post_date)) ? shortDate.format(Date.parse(article.post_date)) : ''}</span>
                  {article.is_paid && <span className="rounded bg-bg-tertiary px-1">付费</span>}
                  {status && <span className={cn('ml-auto', article.status === 'awaiting_terms' ? 'text-warning' : 'text-primary-700')}>{status}</span>}
                </span>
              </button>
            </li>
          );
        })}
        <li ref={sentinel} aria-hidden className="h-px" />
        {library.isFetchingNextPage && (
          <li className="flex justify-center py-3 text-text-muted"><Loader2 className="h-4 w-4 animate-spin" /></li>
        )}
        {otherProjects.length > 0 && (
          <>
            <li className="px-3 pb-1 pt-4 text-xs text-text-muted">不在文章库里的项目</li>
            {otherProjects.map(project => (
              <li key={project.id}>
                <button
                  type="button"
                  onClick={() => onSelectProject(project.id)}
                  className={cn('w-full rounded-md px-3 py-2 text-left text-sm transition-colors', project.id === selectedProjectId ? 'bg-primary-50' : 'hover:bg-bg-hover')}
                >
                  <span className="line-clamp-2 leading-snug text-text-primary">{project.title}</span>
                  <span className="mt-0.5 block text-[11px] text-text-muted">已译 {Math.round(project.progress?.percent ?? 0)}%</span>
                </button>
              </li>
            ))}
          </>
        )}
      </ul>
    </div>
  );
}
