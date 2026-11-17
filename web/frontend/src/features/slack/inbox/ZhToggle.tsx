import { Languages, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useShowZh } from './ai';

/** 「全部中文」开关：开了就在每条英文消息下面显示 AI 中文（默认关，单条可在悬停工具条上点「译」）。 */
export function ZhToggle({ loading = false, failed = false }: { loading?: boolean; failed?: boolean }) {
  const { showZh, toggleZh } = useShowZh();
  return (
    <button
      type="button"
      onClick={toggleZh}
      aria-pressed={showZh}
      title={failed ? '有一部分没翻出来，稍后会重试' : showZh ? '关掉：只在点「译」的消息下显示中文' : '每条英文消息下面都显示中文（单条翻译：鼠标移到消息上点「译」）'}
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors',
        showZh ? 'border-primary-200 bg-primary-50 text-primary-700' : 'border-border-subtle text-text-secondary hover:bg-bg-hover'
      )}
    >
      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Languages className="h-3.5 w-3.5" />}
      {showZh ? '全部中文：开' : '全部中文'}{failed ? ' !' : ''}
    </button>
  );
}
