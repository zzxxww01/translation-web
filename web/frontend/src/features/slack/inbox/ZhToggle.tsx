import { Languages, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useShowZh } from './ai';

/** 「中文」开关：开了就在每条英文消息下面显示 AI 中文。loading 时转圈。 */
export function ZhToggle({ loading = false, failed = false }: { loading?: boolean; failed?: boolean }) {
  const { showZh, toggleZh } = useShowZh();
  return (
    <button
      type="button"
      onClick={toggleZh}
      aria-pressed={showZh}
      title={failed ? '有一部分没翻出来，稍后会重试' : showZh ? '隐藏中文' : '在每条英文下面显示中文'}
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors',
        showZh ? 'border-primary-200 bg-primary-50 text-primary-700' : 'border-border-subtle text-text-secondary hover:bg-bg-hover'
      )}
    >
      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Languages className="h-3.5 w-3.5" />}
      中文{failed ? ' !' : ''}
    </button>
  );
}
