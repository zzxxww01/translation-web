import { useId } from 'react';
import { AlertCircle, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePaneSaveState } from '../lib/edits';
import { FOCUS_RING, STROKE } from '../lib/ui';

const clock = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });

/**
 * 顶栏的保存状态，同时也是保存按钮（Ctrl/⌘+S 一样）：两个中文栏合并显示。
 * 按钮名是「保存」，状态文字作为它的描述读出来；「N 段没保存上」另外播报一次。
 * compact（手机）：平时只显示图标，没保存上时照样写出来。
 */
export function SaveStatus({ saving, onSave, compact = false }: { saving: boolean; onSave: () => void; compact?: boolean }) {
  const main = usePaneSaveState('main');
  const compare = usePaneSaveState('compare');
  const statusId = useId();
  const failed = main.failed + compare.failed;
  const busy = saving || main.busy + compare.busy > 0;
  const savedAt = Math.max(main.savedAt ?? 0, compare.savedAt ?? 0) || null;
  const text = failed ? `${failed} 段没保存上` : busy ? '保存中…' : savedAt ? `已保存 ${clock.format(savedAt)}` : '保存';
  return (
    <>
      <button type="button" aria-label="保存" aria-describedby={text === '保存' ? undefined : statusId}
        title="Ctrl/⌘ + S：立刻保存（改动本来就会自动保存）" disabled={saving} onClick={onSave}
        className={cn('inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg text-[12.5px] tabular-nums transition-colors hover:bg-ink-wash', FOCUS_RING,
          compact && !failed ? 'w-8 justify-center' : 'px-2',
          failed ? 'font-medium text-error' : 'text-text-muted hover:text-text-secondary')}>
        {failed
          ? <AlertCircle aria-hidden className="h-3.5 w-3.5 shrink-0" strokeWidth={STROKE} />
          : <Check aria-hidden className={cn('h-3.5 w-3.5 shrink-0', savedAt && !busy && 'text-success')} strokeWidth={STROKE} />}
        <span id={statusId} className={cn(compact && !failed && 'sr-only')}>{text}</span>
      </button>
      <span role="status" className="sr-only">{failed ? text : ''}</span>
    </>
  );
}
