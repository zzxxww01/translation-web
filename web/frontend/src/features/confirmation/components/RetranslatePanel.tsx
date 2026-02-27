/**
 * 重新翻译面板组件 - 简化增强版
 * 提供快捷指令、自定义指令输入和基础模型选择功能
 */

import { useState, useCallback } from 'react';
import { RefreshCw, Zap, Briefcase, MessageCircle, X, Cpu } from 'lucide-react';
import { Button } from '../../../components/ui';
import { cn } from '../../../shared/utils';

interface RetranslatePanelProps {
  onRetranslate: (instruction: string, model?: string) => Promise<void>;
  isRetranslating?: boolean;
  className?: string;
}

interface QuickInstruction {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  instruction: string;
}

interface ModelOption {
  id: string;
  name: string;
  description: string;
}

const quickInstructions: QuickInstruction[] = [
  {
    id: 'concise',
    label: '更简洁',
    description: '精简冗余表达',
    icon: <Zap className="h-4 w-4" />,
    instruction: '请更简洁地翻译这段文字，删除冗余表达，使译文更加精炼。',
  },
  {
    id: 'professional',
    label: '更专业',
    description: '使用专业术语',
    icon: <Briefcase className="h-4 w-4" />,
    instruction: '请使用更专业的技术术语和行业表达来翻译这段文字。',
  },
  {
    id: 'colloquial',
    label: '更口语化',
    description: '自然流畅表达',
    icon: <MessageCircle className="h-4 w-4" />,
    instruction: '请使用更口语化、更自然的中文表达来翻译这段文字，使其读起来更流畅。',
  },
];

const modelOptions: ModelOption[] = [
  {
    id: 'gemini-3-pro',
    name: 'Gemini 3 Pro',
    description: '最强性能，适合复杂翻译任务',
  },
  {
    id: 'gemini-3-pro-image',
    name: 'Gemini 3 Pro Image',
    description: '图像理解增强版',
  },
  {
    id: 'gemini-3-flash',
    name: 'Gemini 3 Flash',
    description: '快速响应版本',
  },
  {
    id: 'gemini',
    name: 'Gemini (默认)',
    description: '标准翻译模型',
  },
];

export function RetranslatePanel({
  onRetranslate,
  isRetranslating = false,
  className,
}: RetranslatePanelProps) {
  const [customInstruction, setCustomInstruction] = useState('');
  const [selectedInstruction, setSelectedInstruction] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('gemini-3-pro');
  const [showModelSelection, setShowModelSelection] = useState(false);

  const handleQuickInstruction = useCallback(
    async (instruction: QuickInstruction) => {
      setSelectedInstruction(instruction.id);
      try {
        await onRetranslate(instruction.instruction, selectedModel);
      } finally {
        setSelectedInstruction(null);
      }
    },
    [onRetranslate, selectedModel]
  );

  const handleCustomInstruction = useCallback(async () => {
    if (!customInstruction.trim()) {
      return;
    }
    try {
      await onRetranslate(customInstruction.trim(), selectedModel);
    } finally {
      setCustomInstruction('');
    }
  }, [customInstruction, onRetranslate, selectedModel]);

  const selectedModelInfo = modelOptions.find(m => m.id === selectedModel);

  return (
    <div className={cn('rounded-xl border border-border bg-bg-tertiary/50 p-4', className)}>
      {/* 标题 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-text-primary">重新翻译</h3>
        </div>
        <button
          onClick={() => setShowModelSelection(!showModelSelection)}
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          {showModelSelection ? '隐藏模型' : '选择模型'}
        </button>
      </div>

      {/* 模型选择面板 */}
      {showModelSelection && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="mb-2 text-xs font-medium text-gray-700 flex items-center gap-2">
            <Cpu className="h-3 w-3" />
            翻译模型选择
          </div>
          <div className="space-y-2">
            {modelOptions.map((model) => (
              <label
                key={model.id}
                className={cn(
                  'flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors',
                  selectedModel === model.id
                    ? 'border-blue-300 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <input
                  type="radio"
                  name="model"
                  value={model.id}
                  checked={selectedModel === model.id}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="text-blue-600"
                />
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {model.name}
                  </div>
                  <div className="text-xs text-gray-500">
                    {model.description}
                  </div>
                </div>
              </label>
            ))}
          </div>
          {selectedModelInfo && (
            <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-700">
              当前选择: <strong>{selectedModelInfo.name}</strong> - {selectedModelInfo.description}
            </div>
          )}
        </div>
      )}

      {/* 快捷指令 */}
      <div className="mb-3">
        <div className="mb-2 text-xs font-medium text-text-secondary">快捷指令</div>
        <div className="grid grid-cols-3 gap-2">
          {quickInstructions.map((item) => (
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
                {item.icon}
              </div>
              <span className="text-xs font-medium text-text-primary">{item.label}</span>
              <span className="text-[10px] text-text-muted">{item.description}</span>
            </button>
          ))}
        </div>
      </div>

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
          💡 重新翻译会生成一个新的翻译版本，您可以在版本列表中选择最合适的译文。
          {selectedModelInfo && (
            <>
              <br />
              🤖 当前模型: <strong>{selectedModelInfo.name}</strong>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
