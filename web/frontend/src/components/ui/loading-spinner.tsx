import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  return (
    <div className={cn('relative', className)}>
      <div className={cn(
        'animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600',
        size === 'sm' && 'h-4 w-4',
        size === 'md' && 'h-8 w-8',
        size === 'lg' && 'h-12 w-12',
      )} />
      <div className={cn(
        'absolute inset-0 rounded-full bg-indigo-500/10 animate-breathing',
      )} />
    </div>
  );
}
