/**
 * 骨架屏加载组件
 * 用于段落版本加载时的占位符
 */

import { cn } from '../../../shared/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rect' | 'circle';
  width?: string | number;
  height?: string | number;
}

export function Skeleton({
  className,
  variant = 'rect',
  width,
  height,
}: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse bg-muted rounded',
        variant === 'text' && 'h-4 w-full',
        variant === 'rect' && 'rounded-lg',
        variant === 'circle' && 'rounded-full',
        className
      )}
      style={{ width, height }}
    />
  );
}

interface VersionCardSkeletonProps {
  className?: string;
}

export function VersionCardSkeleton({ className }: VersionCardSkeletonProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border-2 bg-card p-4 space-y-3',
        'border-border',
        className
      )}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton variant="circle" width={20} height={20} />
          <Skeleton variant="rect" width={120} height={20} />
        </div>
        <Skeleton variant="rect" width={80} height={24} />
      </div>

      {/* 内容 */}
      <div className="space-y-2">
        <Skeleton variant="text" />
        <Skeleton variant="text" />
        <Skeleton variant="text" width="70%" />
      </div>

      {/* 按钮 */}
      <div className="flex gap-2">
        <Skeleton variant="rect" height={36} className="flex-1" />
        <Skeleton variant="rect" width={80} height={36} />
      </div>
    </div>
  );
}

interface ParagraphSkeletonProps {
  className?: string;
}

export function ParagraphSkeleton({ className }: ParagraphSkeletonProps) {
  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center gap-3 mb-4">
        <Skeleton variant="rect" width={80} height={24} />
        <Skeleton variant="rect" width={120} height={24} />
      </div>
      <div className="space-y-3">
        <Skeleton variant="text" />
        <Skeleton variant="text" />
        <Skeleton variant="text" />
        <Skeleton variant="text" width="80%" />
      </div>
    </div>
  );
}
