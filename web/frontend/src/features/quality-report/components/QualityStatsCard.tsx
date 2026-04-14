/**
 * 质量统计卡片组件
 */

import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface QualityStatsCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

export function QualityStatsCard({ title, value, subtitle, variant = 'default' }: QualityStatsCardProps) {
  const variantStyles = {
    default: 'border-gray-200 bg-white',
    success: 'border-green-200 bg-gradient-to-br from-green-50 to-emerald-50',
    warning: 'border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50',
    error: 'border-red-200 bg-gradient-to-br from-red-50 to-rose-50',
  };

  const valueStyles = {
    default: 'text-gray-900',
    success: 'text-green-700',
    warning: 'text-amber-700',
    error: 'text-red-700',
  };

  return (
    <Card className={cn('border-2', variantStyles[variant])}>
      <CardContent className="p-6">
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={cn('text-3xl font-bold', valueStyles[variant])}>{value}</p>
          {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
