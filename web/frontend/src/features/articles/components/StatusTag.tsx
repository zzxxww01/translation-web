import { cn } from '@/lib/utils';
import { TONE, type StatusTone } from '../lib/tracks';

/** 状态：小圆点 + 文字，翻译中的圆点会呼吸 */
export function StatusTag({ status, className }: { status: { text: string; tone: StatusTone }; className?: string }) {
  return (
    <span className={cn('ml-auto inline-flex items-center gap-1.5', TONE[status.tone].text, className)}>
      <span aria-hidden className={cn('h-1.5 w-1.5 rounded-full', TONE[status.tone].bar, status.tone === 'busy' && 'animate-pulse')} />
      {status.text}
    </span>
  );
}
