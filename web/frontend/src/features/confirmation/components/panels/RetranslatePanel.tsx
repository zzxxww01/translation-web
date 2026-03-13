/**
 * 重新翻译面板组件 - 从后端拉取快捷指令选项
 * 提供快捷指令和自定义指令输入功能
 */

import { useState, useCallback, useEffect } from 'react';
import { RefreshCw, Zap, Briefcase, MessageCircle, X } from 'lucide-react';
import { Button } from '../../../../components/ui';
import { cn } from '../../../../shared/utils';
import { confirmationApi } from '../../api/confirmationApi';

interface RetranslatePanelProps {
  projectId: string;
  onRetranslate: (instruction: string, optionId?: string) => Promise<void>;
  isRetranslating?: boolean;
  className?: string;
}

interface RetranslateOption {
  id: string;
  label: string;
  description: string;
  instruction: string;
}

const iconMap: Record<string, React.ReactNode> = {
  readable: <Zap className="h-4 w-4" />,
  idiomatic: <MessageCircle className="h-4 w-4" />,
  professional: <Briefcase className="h-4 w-4" />,
};

const defaultIcon = <RefreshCw className="h-4 w-4" />;

export function RetranslatePanel({
  projectId,
  onRetranslate,
  isRetranslating = false,
  className,
}: RetranslatePanelProps) {
  const [customInstruction, setCustomInstruction] = useState('');
  const [selectedInstruction, setSelectedInstruction] = useState<string | null>(null);
  const [options, setOptions] = useState<RetranslateOption[]>([]);

  useEffect(() => {
    let cancelled = false;
    confirmationApi.getRetranslateOptions(projectId).then(data => {
      if (!cancelled) {
        setOptions(data.options);
      }
    }).catch(() => {
      // Silently ignore — options will remain empty
    });
    return () => { cancelled = true; };
  }, [projectId]);

  const handleQuickInstruction = useCallback(
    async (option: RetranslateOption) => {
      setSelectedInstruction(option.id);
      try {
        await onRetranslate('', option.id);
      } finally {
        setSelectedInstruction(null);
      }
    },
    [onRetranslate]
  );

  const handleCustomInstruction = useCallback(async () => {
    if (!customInstruction.trim()) {
      return;
    }
    try {
      await onRetranslate(customInstruction.trim());
    } finally {
      setCustomInstruction('');
    }
  }, [customInstruction, onRetranslate]);

  return (
    <div className={cn('rounded-xl border border-border bg-bg-tertiary/50 p-4', className)}>
      {/* 标题 */}
      <div className="mb-3 flex items-center gap-2">
        <RefreshCw className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-text-primary">重新翻译</h3>
      </div>

      {/* 快捷指令 */}
      {options.length > 0 && (
        <div className="mb-3">
          <div className="mb-2 text-xs font-medium text-text-secondary">快捷指令</div>
          <div className="grid grid-cols-3 gap-2">
            {options.map((item) => (
              <button
                key={item.id}
                onClick={() => handleQuickInstruction(item)}
                disabled={isRetranslating}
                className={cn(
                  'flex flex-col items-center gap-1 rounded-lg border p-2 transition-all',
                  'hover:border-primary/50 hover:bg-primary/5',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  selectedInstruction === item.id && isRetranslating
                    ? 'border-primary bg-primary/10'
                    : 'border-border'
                )}
              >
                <div className={cn(
                  'rounded-full p-1.5',
                  selectedInstruction === item.id && isRetranslating
                    ? 'bg-primary text-white'
                    : 'bg-bg-hover text-text-secondary'
                )}>
                  {iconMap[item.id] ?? defaultIcon}
                </div>
                <span className="text-xs font-medium text-text-primary">{item.label}</span>
                <span className="text-[10px] text-text-muted">{item.description}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 自定义指令 */}
      <div>
        <div className="mb-2 text-xs font-medium text-text-secondary">自定义指令</div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              placeholder="输入自定义翻译指令..."
              disabled={isRetranslating}
              className={cn(
                'w-full rounded-lg border border-border px-3 py-2 pr-8 text-sm',
                'bg-bg-tertiary text-text-primary',
                'focus:outline-none focus:ring-2 focus:ring-primary-500',
                'placeholder:text-text-muted',
                'disabled:opacity-50'
              )}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleCustomInstruction();
                }
              }}
            />
            {customInstruction && (
              <button
                onClick={() => setCustomInstruction('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-text-muted hover:text-text-primary hover:bg-bg-hover"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
          <Button
            variant="primary"
            size="md"
            onClick={handleCustomInstruction}
            disabled={!customInstruction.trim() || isRetranslating}
            isLoading={isRetranslating && !selectedInstruction}
            leftIcon={<RefreshCw className="h-4 w-4" />}
          >
            翻译
          </Button>
        </div>
      </div>

      {/* 提示信息 */}
      <div className="mt-3 rounded-lg bg-info/10 p-2">
        <p className="text-[10px] text-info">
          重新翻译会生成一个新的翻译版本，您可以在版本列表中选择最合适的译文。
        </p>
      </div>
    </div>
  );
}
