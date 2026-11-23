import { useState } from 'react';
import { FileText, Hash, Loader2, Plus, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDraftList, type DraftSummary, type SentFilter } from '../drafts';

function when(ts: number): string {
  const d = new Date(ts * 1000);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  }
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function statusText(item: Pick<DraftSummary, 'status' | 'auto' | 'seen' | 'sent' | 'sent_at' | 'sent_auto' | 'sent_changed'>): string {
  if (item.sent ?? item.sent_at) {
    if (item.sent_auto) return '已发送（超过两周）';
    return item.sent_changed ? '已发送 · 发送后有改动' : '已发送';
  }
  if (item.status === 'done') return '未发送 · 已完成';
  return item.auto && !item.seen ? '未发送 · 自动翻好' : '未发送 · 草稿';
}

const SENT_FILTERS: { id: SentFilter; label: string; hint: string }[] = [
  { id: '', label: '全部', hint: '全部翻译记录' },
  { id: 'no', label: '未发送', hint: '两周内还没标已发送的；超过两周的默认已发送' },
  { id: 'yes', label: '已发送', hint: '标了已发送的，加上超过两周的' },
];

/**
 * 翻译记录：帖子翻译页手动翻的和 Slack 里翻的合在一起，按最近修改排。点一条打开（Slack 的跳到 Slack 翻译模式）。
 * 不提供删除（2026-11-22 用户要求）。
 */
export function DraftHistory({ activeId, onOpen, onNew }: {
  activeId: string | null;
  onOpen: (item: DraftSummary) => void;
  /** 不传就不显示「新建」（Slack 里的全部翻译记录） */
  onNew?: () => void;
}) {
  const [q, setQ] = useState('');
  const [sent, setSent] = useState<SentFilter>('');
  const list = useDraftList(q.trim(), sent);

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-2 border-b border-border-subtle p-3">
        {onNew && <button
          type="button"
          onClick={onNew}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-primary-200 bg-primary-50/50 py-2 text-sm text-primary-700 transition-colors hover:bg-primary-50"
        >
          <Plus className="h-4 w-4" /> 新建（粘贴原文）
        </button>}
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
        <div className="flex gap-1" role="group" aria-label="按发送状态筛选">
          {SENT_FILTERS.map(f => (
            <button
              key={f.id || 'all'}
              type="button"
              onClick={() => setSent(f.id)}
              title={f.hint}
              aria-pressed={sent === f.id}
              className={cn(
                'rounded-full px-2.5 py-0.5 text-xs transition-colors',
                sent === f.id ? 'bg-primary-500 text-white' : 'text-text-secondary hover:bg-bg-hover'
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {list.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {list.data && list.data.length === 0 && (
          <div className="px-4 py-10 text-center text-sm text-text-muted">
            {q ? '没有找到' : sent === 'no' ? '两周内的都标了已发送' : sent === 'yes' ? '还没有已发送的' : '还没有翻译记录。翻出第一版译文后会自动存进来。'}
          </div>
        )}
        {list.data?.map(item => (
          <div
            key={item.id}
            className={cn(
              'border-b border-border-subtle transition-colors',
              item.id === activeId ? 'bg-primary-50' : item.auto && !item.seen ? 'bg-primary-50/40 hover:bg-primary-50/70' : 'hover:bg-bg-hover'
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
                  <span className="shrink-0 text-[11px] text-text-muted">{when(item.updated_at)}</span>
                </div>
                <div className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-text-secondary">
                  {item.preview || item.source_preview || '还没有译文'}
                </div>
                <div className="mt-1 truncate text-[11px] text-text-muted">
                  {[
                    item.source === 'slack' ? 'Slack' : '手动',
                    statusText(item),
                    item.image_count > 0 ? `${item.image_count} 张图` : '',
                  ].filter(Boolean).join(' · ')}
                </div>
              </div>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
