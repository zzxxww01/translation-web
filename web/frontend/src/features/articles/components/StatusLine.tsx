import { Fragment } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TONE_DOT } from '../lib/tones';
import { FOCUS_RING, STROKE } from '../lib/ui';
import type { Tone, VersionAction, VersionView } from '../lib/versions';

const TONE_TEXT: Record<Tone, string> = {
  done: 'text-text-muted', busy: 'text-text-muted', idle: 'text-text-muted', wait: 'text-warning-text', error: 'text-error',
};

const LEADS_SOMEWHERE = new Set<VersionAction['kind']>(['confirm-terms', 'open-run', 'login']);

/**
 * 版本名下面那一行：「● 状态 · 模型 · 补充 · 行动」。所有状态都写在这里，不另外弹提示。
 * 桌面上一行放不下时只截断说明文字（悬停看全文），行动链接始终完整可点；
 * 手机上没有悬停，改成自然换行，整句都看得到。
 */
export function StatusLine({ version, onAction }: { version: VersionView; onAction: (action: VersionAction) => void }) {
  const text = version.line.join(' · ');
  return (
    <p className={cn('text-[12px] leading-5 md:flex md:min-w-0 md:items-center md:gap-1.5', TONE_TEXT[version.tone])}>
      <span aria-hidden className={cn('mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-[0.1em] md:mr-0 md:shrink-0', TONE_DOT[version.tone])} />
      <span className="md:min-w-0 md:truncate" title={text}>{text}</span>
      {version.actions.map(action => (
        <Fragment key={action.label}>
          <span aria-hidden className="mx-1.5 text-text-disabled md:mx-0 md:shrink-0">·</span>
          <button type="button" onClick={() => onAction(action)}
            className={cn('inline-flex shrink-0 items-center gap-0.5 whitespace-nowrap rounded-sm font-medium text-primary-700 underline-offset-[3px] hover:underline', FOCUS_RING)}>
            {action.label}
            {LEADS_SOMEWHERE.has(action.kind) && <ArrowRight aria-hidden className="h-3 w-3" strokeWidth={STROKE} />}
          </button>
        </Fragment>
      ))}
    </p>
  );
}
