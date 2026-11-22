import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import type { SubstackArticle } from '@/features/substack/api';
import { useLibrary } from '../hooks';
import { articleStatus, TONE } from '../lib/tracks';
import { StatusTag } from './StatusTag';

const today = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' });
const shortDate = new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' });
const IN_PROGRESS = new Set(['imported', 'awaiting_terms', 'translating', 'partial']);

interface ArticleDeskProps {
  onSelectArticle: (article: SubstackArticle) => void;
  onSelectProject: (projectId: string) => void;
}

/**
 * 「今天的桌面」：文章页没选文章时右边不再空着，列出进行中的翻译、新到的文章、最近译完的。
 * 数据就是侧栏同一个文章库接口的第一页（已导入 / 未导入两个筛选），和侧栏共用缓存。
 */
export function ArticleDesk({ onSelectArticle, onSelectProject }: ArticleDeskProps) {
  const imported = useLibrary('imported', '');
  const fresh = useLibrary('not_imported', '');
  const importedList = imported.data?.pages[0]?.articles ?? [];
  const counts = imported.data?.pages[0]?.counts ?? fresh.data?.pages[0]?.counts;
  const working = importedList.filter(article => IN_PROGRESS.has(article.status)).slice(0, 4);
  const done = importedList.filter(article => article.status === 'translated').slice(0, 4);
  const newest = (fresh.data?.pages[0]?.articles ?? []).slice(0, 4);
  const open = (article: SubstackArticle) => (article.project_id ? onSelectProject(article.project_id) : onSelectArticle(article));
  const loading = imported.isPending || fresh.isPending;

  return (
    <div className="mx-auto w-full max-w-[920px] px-8 pb-16 pt-10">
      <p className="text-xs tracking-wide text-text-muted">{today.format(new Date())}</p>
      <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold text-text-primary">今天的桌面</h1>
      {counts && (
        <p className="mt-2 text-sm text-text-muted">
          文章库 <b className="font-medium tabular-nums text-text-secondary">{counts.all ?? '—'}</b> 篇 · 已导入{' '}
          <b className="font-medium tabular-nums text-text-secondary">{counts.imported ?? '—'}</b> · 未导入{' '}
          <b className="font-medium tabular-nums text-text-secondary">{counts.not_imported ?? '—'}</b>
        </p>
      )}

      {loading && <p className="mt-10 text-sm text-text-muted">正在摆桌面…</p>}

      {working.length > 0 && (
        <DeskSection title="进行中" note="点开继续翻译或确认术语">
          <div className="grid gap-3 sm:grid-cols-2">
            {working.map(article => {
              const status = articleStatus(article.status, article.progress);
              return (
                <DeskCard key={article.url} article={article} onOpen={open}>
                  {status && (
                    <>
                      <span className="mt-3 flex items-center text-xs"><StatusTag status={status} className="ml-0" /></span>
                      <span className="mt-2 block h-1 overflow-hidden rounded-full bg-bg-inset" aria-hidden>
                        <span className={cn('block h-full rounded-full', TONE[status.tone].bar)} style={{ width: `${Math.max(status.percent, 2)}%` }} />
                      </span>
                    </>
                  )}
                </DeskCard>
              );
            })}
          </div>
        </DeskSection>
      )}

      {newest.length > 0 && (
        <DeskSection title="新到的文章" note="还没导入，点开先看摘要">
          <div className="grid gap-3 sm:grid-cols-2">
            {newest.map(article => (
              <DeskCard key={article.url} article={article} onOpen={open}>
                {article.zh_summary && <span className="mt-2 line-clamp-2 text-[13px] leading-relaxed text-text-secondary">{article.zh_summary}</span>}
              </DeskCard>
            ))}
          </div>
        </DeskSection>
      )}

      {done.length > 0 && (
        <DeskSection title="最近译完">
          <ul className="divide-y divide-border-subtle overflow-hidden rounded-xl bg-bg-card shadow-paper">
            {done.map(article => (
              <li key={article.url}>
                <button type="button" onClick={() => open(article)} className="flex w-full items-baseline gap-4 px-5 py-3 text-left transition-colors hover:bg-bg-hover">
                  <span className="min-w-0 flex-1 truncate font-[family-name:var(--font-display)] text-[15px] font-semibold text-text-primary">{article.zh_title || article.title}</span>
                  <span className="shrink-0 text-xs tabular-nums text-text-muted">{formatDate(article.post_date)}</span>
                </button>
              </li>
            ))}
          </ul>
        </DeskSection>
      )}

      <p className="mt-12 text-center text-xs text-text-disabled">从左边选一篇文章开始：已导入的直接打开对照编辑，没导入的先看摘要、一键导入翻译。</p>
    </div>
  );
}

function formatDate(value: string): string {
  return Number.isFinite(Date.parse(value)) ? shortDate.format(Date.parse(value)) : '';
}

function DeskSection({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="mt-10">
      <div className="mb-3 flex items-baseline gap-3 border-b border-border-subtle pb-2">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-text-primary">{title}</h2>
        {note && <span className="text-xs text-text-muted">{note}</span>}
      </div>
      {children}
    </section>
  );
}

function DeskCard({ article, onOpen, children }: { article: SubstackArticle; onOpen: (article: SubstackArticle) => void; children?: ReactNode }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(article)}
      className="group flex flex-col rounded-xl bg-bg-card p-4 text-left shadow-paper transition-[box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:shadow-pop focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="flex items-center gap-2 text-[11px] text-text-muted">
        <span className="tabular-nums">{formatDate(article.post_date)}</span>
        {article.is_paid && <span className="rounded border border-border px-1 leading-4">付费</span>}
      </span>
      <span className="mt-1.5 line-clamp-2 font-[family-name:var(--font-display)] text-base font-semibold leading-snug text-text-primary group-hover:text-primary-700">
        {article.zh_title || article.title}
      </span>
      {article.zh_title && <span className="mt-1 truncate font-[family-name:var(--font-source)] text-[13px] italic text-text-muted">{article.title}</span>}
      {children}
    </button>
  );
}
