import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ExternalLink, Hash, Loader2, Lock, MessageCircle, Search, Users } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { slackInboxApi } from './api';
import { clockTime, dayLabel, emojify } from './lib';
import type { SlackSearchResult } from './types';

interface SearchViewProps {
  query: string;
  onSearch: (q: string) => void;
  onOpen: (channelId: string, threadTs: string | null) => void;
  onBack: () => void;
}

function KindIcon({ result }: { result: SlackSearchResult }) {
  const cls = 'h-3.5 w-3.5 shrink-0';
  if (result.kind === 'private') return <Lock className={cls} />;
  if (result.kind === 'mpim') return <Users className={cls} />;
  if (result.kind === 'im') return <MessageCircle className={cls} />;
  return <Hash className={cls} />;
}

/** 搜索：中文也行，AI 先改写成英文关键词，再用 Slack 自己的搜索，按时间倒序。 */
export function SearchView({ query, onSearch, onOpen, onBack }: SearchViewProps) {
  const [draft, setDraft] = useState(query);
  const result = useQuery({
    queryKey: ['slack-inbox', 'search', query],
    queryFn: () => slackInboxApi.search(query),
    enabled: !!query.trim(),
    staleTime: 60_000,
  });

  const open = (r: SlackSearchResult) => {
    if (r.visible) onOpen(r.channel_id, r.thread_ts);
    else window.open(r.message.permalink, '_blank', 'noopener');
  };

  return (
    <>
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2">
        <Button variant="ghost" size="sm" className="h-7 px-1.5 md:hidden" onClick={onBack} aria-label="返回会话列表">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <form
          className="flex min-w-0 flex-1 items-center gap-2"
          onSubmit={e => {
            e.preventDefault();
            if (draft.trim()) onSearch(draft.trim());
          }}
        >
          <Search className="h-4 w-4 shrink-0 text-text-muted" />
          <input
            value={draft}
            onChange={e => setDraft(e.target.value)}
            placeholder="搜 Slack，中文也行，例如：英伟达 Rubin 的 HBM 容量"
            className="min-w-0 flex-1 bg-transparent py-1 text-sm text-text-primary outline-none placeholder:text-text-muted"
            aria-label="搜索 Slack"
          />
          <Button type="submit" size="sm" className="h-7" disabled={!draft.trim()}>搜索</Button>
        </form>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {result.isFetching && (
          <div className="flex items-center gap-2 px-5 py-4 text-sm text-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> 搜索中…
          </div>
        )}
        {result.isError && <div className="px-5 py-4 text-sm text-error">搜索失败：{result.error.message}</div>}
        {result.data && (
          <div className="border-b border-border-subtle px-5 py-2 text-xs text-text-muted">
            {result.data.query !== result.data.input && <>按英文关键词「<span className="font-medium text-text-secondary">{result.data.query}</span>」搜索 · </>}
            共 {result.data.total} 条，显示最近 {result.data.results.length} 条
          </div>
        )}
        {result.data?.results.length === 0 && <div className="px-5 py-6 text-sm text-text-muted">没找到，换几个关键词试试</div>}
        {result.data?.results.map(r => (
          <button
            key={`${r.channel_id}-${r.message.ts}`}
            type="button"
            onClick={() => open(r)}
            className="block w-full border-b border-border-subtle px-5 py-2.5 text-left hover:bg-bg-hover/60"
          >
            <div className="flex items-center gap-1.5 text-xs text-text-muted">
              <KindIcon result={r} />
              <span className="font-medium text-text-secondary">{r.channel_name}</span>
              {r.thread_ts && <span>· thread 回复</span>}
              <span>· {r.message.user_name}</span>
              <span className="ml-auto shrink-0">{dayLabel(r.message.ts)} {clockTime(r.message.ts)}</span>
              {!r.visible && <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-label="在 Slack 里打开" />}
            </div>
            <div className="mt-0.5 line-clamp-3 whitespace-pre-wrap text-sm text-text-primary">{emojify(r.message.text)}</div>
          </button>
        ))}
      </div>
    </>
  );
}
