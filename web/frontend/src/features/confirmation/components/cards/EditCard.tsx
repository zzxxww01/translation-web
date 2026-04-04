/**
 * 编辑卡片组件
 * 允许用户自定义编辑译文
 */

import { useState } from 'react';
import { cn } from '@/shared/utils';
import { Button } from '@/components/ui/button-extended';
import { Textarea } from '@/components/ui/textarea';

interface EditCardProps {
  value: string;
  onChange: (value: string) => void;
  onConfirm: (translation: string) => void;
  className?: string;
}

export function EditCard({ value, onChange, onConfirm, className }: EditCardProps) {
  const [isFocused, setIsFocused] = useState(false);

  const handleConfirm = () => {
    if (value.trim()) {
      onConfirm(value);
    }
  };

  return (
    <div
      className={cn(
        'rounded-2xl border-2 bg-card p-4 transition-all',
        isFocused ? 'ring-2 ring-primary border-primary' : 'border-border',
        className
      )}
    >
      {/* 头部 */}
      <div className="mb-3 flex items-center gap-2">
        <span className="text-lg" role="img" aria-label="edit-icon">
          ✏️
        </span>
        <span className="font-semibold text-text-primary">自定义编辑</span>
      </div>

      {/* 编辑区域 */}
      <div className="mb-3">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="在此编辑或输入自定义译文..."
          className="min-h-[120px] resize-y"
        />
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <Button
          variant="default"
          size="sm"
          onClick={handleConfirm}
          disabled={!value.trim()}
          className="flex-1"
        >
          确认并保存
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange('')}
          disabled={!value}
        >
          清空
        </Button>
      </div>
    </div>
  );
}
