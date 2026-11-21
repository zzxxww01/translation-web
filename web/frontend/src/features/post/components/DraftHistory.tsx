import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { FileText, Hash, Loader2, Plus, Search, Sparkles, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { draftsApi, useDraftList, type DraftSummary } from '../drafts';

function when(ts: number): string {
  const d = new Date(ts * 1000);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  }
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function StatusBadge({ item }: { item: Pick<DraftSummary, 'status' | 'auto' | 'seen'> }) {
  if (item.status === 'done') {
    return <span className="shrink-0 rounded-full bg-success/10 px-1.5 text-[10px] font-medium leading-4 text-success">✓ 已完成</span>;
  }
  if (item.auto && !item.seen) {
    return <span className="shrink-0 rounded-full bg-primary-500 px-1.5 text-[10px] font-medium leading-4 text-white">自动翻好 · 待查看</span>;
  }
  return <span className="shrink-0 rounded-full bg-amber-100 px-1.5 text-[10px] font-medium leading-4 text-amber-800">草稿</span>;
}

/**
 * 翻译记录：帖子翻译页手动翻的和 Slack 里翻的合在一起，按最近修改排。点一条打开（Slack 的跳到 Slack 翻译模式）。
 */
export function DraftHistory({ activeId, onOpen, onNew }: {
  activeId: string | null;
  onOpen: (item: DraftSummary) => void;
  onNew: () => void;
}) {
  const [q, setQ] = useState('');
  const list = useDraftList(q.trim());
  const queryClient = useQueryClient();

  const remove = async (item: DraftSummary) => {
    if (!window.confirm(`删除「${item.title || '这篇翻译'}」？删除后找不回来。`)) return;
    await draftsApi.remove(item.id);
    void queryClient.invalidateQueries({ queryKey: ['post-drafts'] });
    toast.success('已删除');
  };

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-2 border-b border-border-subtle p-3">
        <button
          type="button"
          onClick={onNew}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-primary-200 bg-primary-50/50 py-2 text-sm text-primary-700 transition-colors hover:bg-primary-50"
        >
          <Plus className="h-4 w-4" /> 新建（粘贴原文）
        </button>
        <label className="flex items-center gap-1.5 rounded-lg border border-border-subtle bg-white px-2.5">
          <Search className="h-3.5 w-3.5 shrink-0 text-text-muted" />
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="搜标题、原文、译文"
            aria-label="搜索翻译记录"
            className="min-w-0 flex-1 bg-transparent py-1.5 text-sm outline-none placeholder:text-text-muted"
          />
        </label>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {list.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {list.data && list.data.length === 0 && (
          <div className="px-4 py-10 text-center text-sm text-text-muted">
            {q ? '没有找到' : '还没有翻译记录。翻出第一版译文后会自动存进来。'}
          </div>
        )}
        {list.data?.map(item => (
          <div
            key={item.id}
            className={cn(
              'group relative border-b border-border-subtle transition-colors',
              item.id === activeId ? 'bg-primary-50' : 'hover:bg-bg-hover'
            )}
          >
            <button type="button" onClick={() => onOpen(item)} className="flex w-full gap-3 px-3 py-2.5 text-left">
              {item.images[0] ? (
                <img
                  src={`/api/slack-inbox/files/${item.images[0]}`}
                  alt=""
                  loading="lazy"
                  className="h-12 w-12 shrink-0 rounded-md border border-border-subtle bg-bg-tertiary object-cover"
                />
              ) : (
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-bg-tertiary text-text-muted">
                  {item.source === 'slack' ? <Hash className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-text-primary">{item.title || '（无标题）'}</span>
                  <StatusBadge item={item} />
                </div>
                <div className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-text-secondary">
                  {item.preview || item.source_preview || '还没有译文'}
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-[11px] text-text-muted">
                  {item.source === 'slack'
                    ? <span className="inline-flex items-center gap-0.5"><Sparkles className="h-3 w-3" />Slack{item.slack?.channel_name ? ` · #${item.slack.channel_name}` : ''}</span>
                    : <span>手动</span>}
                  <span>· v{item.versions}</span>
                  {item.image_count > 0 && <span>· {item.image_count} 张图</span>}
                  <span className="ml-auto">{when(item.updated_at)}</span>
                </div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => void remove(item)}
              className="absolute right-2 top-2 hidden rounded-md bg-white/90 p-1 text-text-muted shadow-sm hover:text-error group-hover:block"
              title="删除这条记录"
              aria-label="删除这条记录"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
