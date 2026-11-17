import { useSearchParams } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { InboxView } from './inbox/InboxView';
import { SLACK_VIEWS as VIEWS, parseSlackView, type SlackView } from './inbox/lib';
import { ReplyWorkbench } from './ReplyWorkbench';

/** Slack 页：频道、私信（只读展示 Slack 消息）和原来的回复工作台。 */
export function SlackFeature() {
  const [params, setParams] = useSearchParams();
  const view = parseSlackView(params.get('view'));
  const selectedId = params.get('c');

  const update = (next: { view?: SlackView; c?: string | null }) => {
    const p = new URLSearchParams(params);
    if (next.view) {
      p.set('view', next.view);
      p.delete('c');
    }
    if (next.c !== undefined) {
      if (next.c) p.set('c', next.c);
      else p.delete('c');
    }
    setParams(p, { replace: true });
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-1 border-b border-border-subtle px-4 sm:px-8" role="tablist" aria-label="Slack 子页面">
        {VIEWS.map(v => (
          <button
            key={v.id}
            type="button"
            role="tab"
            aria-selected={view === v.id}
            onClick={() => update({ view: v.id })}
            className={cn(
              'relative px-3 py-2.5 text-sm transition-colors after:absolute after:inset-x-3 after:-bottom-px after:h-0.5 after:rounded-full',
              view === v.id ? 'font-medium text-text-primary after:bg-primary-500' : 'text-text-muted hover:text-text-primary'
            )}
          >
            {v.label}
          </button>
        ))}
      </div>
      <div className={cn('min-h-0 flex-1', view === 'reply' ? 'overflow-auto' : 'overflow-hidden')}>
        {view === 'reply' ? (
          <ReplyWorkbench />
        ) : (
          <InboxView scope={view} selectedId={selectedId} onSelect={c => update({ c })} />
        )}
      </div>
    </div>
  );
}
