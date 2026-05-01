/**
 * 导航控制组件
 * 提供上一段/下一段导航按钮
 */

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/shared/utils';
import { Button } from '@/components/ui/button-extended';

interface NavigationControlsProps {
  currentIndex: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
  className?: string;
}

export function NavigationControls({
  currentIndex,
  total,
  onPrev,
  onNext,
  className,
}: NavigationControlsProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Button
        variant="outline"
        size="sm"
        onClick={onPrev}
        disabled={currentIndex <= 0}
        leftIcon={<ChevronLeft size={16} />}
      >
        上一段
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={onNext}
        disabled={currentIndex >= total - 1}
        rightIcon={<ChevronRight size={16} />}
      >
        下一段
      </Button>
    </div>
  );
}
