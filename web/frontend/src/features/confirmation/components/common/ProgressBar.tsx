/**
 * 进度条组件
 * 显示翻译进度并支持点击跳转
 */

import { cn } from '../../../../shared/utils';

interface ProgressBarProps {
  current: number;
  total: number;
  onJump?: (index: number) => void;
  className?: string;
}

export function ProgressBar({ current, total, onJump, className }: ProgressBarProps) {
  const progress = total > 0 ? (current / total) * 100 : 0;

  const handleClick = () => {
    if (onJump) {
      onJump(current);
    }
  };

  return (
    <div className={cn('flex items-center gap-4', className)}>
      {/* 进度条 */}
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-text-secondary">
            进度: {current}/{total} ({progress.toFixed(1)}%)
          </span>
        </div>
        <div
          className={cn(
            'h-2 w-full rounded-full bg-muted overflow-hidden',
            onJump && 'cursor-pointer hover:opacity-80 transition-opacity'
          )}
          onClick={handleClick}
          role={onJump ? 'button' : undefined}
          tabIndex={onJump ? 0 : undefined}
        >
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-primary-600 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}
