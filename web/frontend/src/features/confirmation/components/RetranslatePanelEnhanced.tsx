/**
 * 重新翻译面板组件 - 增强版
 * 提供快捷指令、自定义指令输入和模型选择功能
 */

import { useState, useCallback, useEffect } from 'react';
import { RefreshCw, Zap, Briefcase, MessageCircle, X, Cpu, Sparkles, Clock, Image } from 'lucide-react';
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
  icon: React.ReactNode;
  recommended_for: string[];
  max_tokens: number;
}

const quickInstructions: QuickInstruction[] = [
  {
    id: 'readable',
    label: '可读性',
    description: '消除翻译腔',
    icon: <Zap className="h-4 w-4" />,
    instruction: '请从句法结构层面优化译文：拆长句（控制在15-30字）、去被动语态改主动、删多余连接词（"此外""然而"）、调整为中文语序、直接用动词不要"对……进行……"、连续三个"的"必须拆句。',
  },
  {
    id: 'idiomatic',
    label: '更地道',
    description: '自然流畅表达',
    icon: <MessageCircle className="h-4 w-4" />,
    instruction: '请从表达层面优化译文：用具体事实代替空泛描述、用简单结构代替复杂绕行、不要公式化段落和同义词循环、把"基于""鉴于""旨在"换成"根据""考虑到""为了"等自然表达。',
  },
  {
    id: 'professional',
    label: '更专业',
    description: '科技媒体风格',
    icon: <Briefcase className="h-4 w-4" />,
    instruction: '请优化译文的专业表达，体现semiAnalysis分析师水准：保留原文观点和判断力度不要弱化、产品/技术代号保留英文（CoWoS、HBM、EUV）行业术语用中文（晶圆代工、良率）金融术语用中文（营收、毛利率）、删除口水话和宣传腔、数据密集段落拆分重组。',
  },
];

const modelOptions: ModelOption[] = [
  {
    id: 'gemini-3-pro',
    name: 'Gemini 3 Pro',
    description: '最强性能，适合复杂翻译任务',
    icon: <Sparkles className="h-4 w-4" />,
    recommended_for: ['complex_translation', 'academic_text', 'professional_document'],
    max_tokens: 32768,
  },
  {
    id: 'gemini-3-pro-image',
    name: 'Gemini 3 Pro Image',
    description: '图像理解增强版，适合含图表的文档',
    icon: <Image className="h-4 w-4" />,
    recommended_for: ['multimodal_content', 'scientific_paper', 'presentation'],
    max_tokens: 32768,
  },
  {
    id: 'gemini-3-flash',
    name: 'Gemini 3 Flash',
    description: '快速响应版本，适合批量处理',
    icon: <Clock className="h-4 w-4" />,
    recommended_for: ['batch_processing', 'real_time_translation', 'simple_content'],
    max_tokens: 8192,
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
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

  // 获取可用模型列表（模拟API调用）
  const [availableModels, setAvailableModels] = useState<ModelOption[]>(modelOptions);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  useEffect(() => {
    // 模拟获取可用模型
    const fetchAvailableModels = async () => {
      setIsLoadingModels(true);
      try {
        // 这里应该调用实际的API
        // const response = await fetch('/api/models/available');
        // const data = await response.json();
        // setAvailableModels(data.models);

        // 暂时使用静态数据
        await new Promise(resolve => setTimeout(resolve, 500));
        setAvailableModels(modelOptions);
      } catch (error) {
        console.error('Failed to load models:', error);
      } finally {
        setIsLoadingModels(false);
      }
    };

    fetchAvailableModels();
  }, []);

  const handleQuickInstruction = useCallback(
    async (instruction: QuickInstruction) => {
      setSelectedInstruction(instruction.id);
      await onRetranslate(instruction.instruction, selectedModel);
    },
    [onRetranslate, selectedModel]
  );

  const handleCustomInstruction = useCallback(async () => {
    if (!customInstruction.trim()) {
      return;
    }
    await onRetranslate(customInstruction.trim(), selectedModel);
  }, [customInstruction, onRetranslate, selectedModel]);

  const selectedModelInfo = availableModels.find(m => m.id === selectedModel);

  return (
    <div className={cn('rounded-xl border border-border bg-bg-tertiary/50 p-4', className)}>
      {/* 标题 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-text-primary">重新翻译</h3>
        </div>
        <button
          onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          {showAdvancedOptions ? '收起选项' : '高级选项'}
        </button>
      </div>

      {/* 模型选择（高级选项） */}
      {showAdvancedOptions && (
        <div className="mb-4">
          <div className="mb-2 text-xs font-medium text-text-secondary flex items-center gap-2">
            <Cpu className="h-3 w-3" />
            模型选择
          </div>
          <div className="space-y-2">
            {isLoadingModels ? (
              <div className="text-xs text-text-muted">加载模型列表...</div>
            ) : (
              availableModels.map((model) => (
                <label
                  key={model.id}
                  className={cn(
                    'flex items-center gap-3 p-2 rounded-lg border cursor-pointer transition-all',
                    'hover:border-primary/50 hover:bg-primary/5',
                    selectedModel === model.id
                      ? 'border-primary bg-primary/10'
                      : 'border-border'
                  )}
                >
                  <input
                    type="radio"
                    name="model"
                    value={model.id}
                    checked={selectedModel === model.id}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="sr-only"
                  />
                  <div className={cn(
                    'rounded-full p-1.5 flex-shrink-0',
                    selectedModel === model.id
                      ? 'bg-primary text-white'
                      : 'bg-bg-hover text-text-secondary'
                  )}>
                    {model.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-text-primary">
                        {model.name}
                      </span>
                      {selectedModel === model.id && (
                        <span className="text-xs text-primary">✓</span>
                      )}
                    </div>
                    <div className="text-[10px] text-text-muted mt-0.5">
                      {model.description}
                    </div>
                  </div>
                </label>
              ))
            )}
          </div>

          {/* 选中模型的详细信息 */}
          {selectedModelInfo && (
            <div className="mt-2 p-2 bg-info/10 rounded-lg">
              <div className="text-[10px] text-info">
                <strong>当前选择:</strong> {selectedModelInfo.name}<br />
                <strong>最大tokens:</strong> {selectedModelInfo.max_tokens.toLocaleString()}<br />
                <strong>适用场景:</strong> {selectedModelInfo.recommended_for.join(', ')}
              </div>
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
            重新翻译
          </Button>
        </div>
      </div>

      {/* 提示信息 */}
      <div className="mt-3 rounded-lg bg-info/10 p-2">
        <p className="text-[10px] text-info">
          💡 重新翻译会生成一个新的翻译版本，您可以在版本列表中选择最合适的译文。
          {showAdvancedOptions && (
            <>
              <br />
              🤖 当前使用模型: <strong>{selectedModelInfo?.name}</strong>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
