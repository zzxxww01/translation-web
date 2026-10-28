import { Fragment } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TONE_DOT } from '../lib/tones';
import type { Tone, VersionAction, VersionView } from '../lib/versions';

const TONE_TEXT: Record<Tone, string> = {
  done: 'text-text-muted', busy: 'text-text-muted', idle: 'text-text-muted', wait: 'text-[#94600f]', error: 'text-error',
};

const LEADS_SOMEWHERE = new Set<VersionAction['kind']>(['confirm-terms', 'open-run', 'login']);

/** 版本名下面那一行：「● 状态 · 模型 · 补充 · 行动」。所有状态都写在这里，不另外弹提示。 */
export function StatusLine({ version, onAction }: { version: VersionView; onAction: (action: VersionAction) => void }) {
  const text = version.line.join(' · ');
  return (
    <p className={cn('mt-1.5 flex min-w-0 items-center gap-1.5 text-[12px] leading-5', TONE_TEXT[version.tone])} title={text}>
      <span aria-hidden className={cn('h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[version.tone])} />
      <span className="min-w-0 truncate">{text}</span>
      {version.actions.map(action => (
        <Fragment key={action.label}>
          <span aria-hidden className="text-text-disabled">·</span>
          <button type="button" onClick={() => onAction(action)}
            className="inline-flex shrink-0 items-center gap-0.5 text-primary-700 underline-offset-2 hover:underline">
            {action.label}
            {LEADS_SOMEWHERE.has(action.kind) && <ArrowRight className="h-3 w-3" />}
          </button>
        </Fragment>
      ))}
    </p>
  );
}
