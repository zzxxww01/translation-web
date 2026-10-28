import { AlertCircle, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePaneSaveState } from '../lib/edits';

const clock = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });

/** 顶栏的保存状态，同时也是保存按钮（Ctrl/⌘+S 一样）：两个中文栏合并显示 */
export function SaveStatus({ saving, onSave }: { saving: boolean; onSave: () => void }) {
  const main = usePaneSaveState('main');
  const compare = usePaneSaveState('compare');
  const failed = main.failed + compare.failed;
  const busy = saving || main.busy + compare.busy > 0;
  const savedAt = Math.max(main.savedAt ?? 0, compare.savedAt ?? 0) || null;
  const text = failed ? `${failed} 段没保存上` : busy ? '保存中…' : savedAt ? `已保存 ${clock.format(savedAt)}` : '保存';
  return (
    <button type="button" aria-label="保存" title="Ctrl/⌘ + S：立刻保存（改动本来就会自动保存）" disabled={saving} onClick={onSave}
      className={cn('inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-[12.5px] transition-colors hover:bg-[rgba(43,39,48,0.05)]',
        failed ? 'text-error' : 'text-text-muted')}>
      {failed ? <AlertCircle className="h-3.5 w-3.5" /> : <Check className={cn('h-3.5 w-3.5', savedAt && 'text-success')} />}
      {text}
    </button>
  );
}
