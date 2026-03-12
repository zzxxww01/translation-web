/**
 * 重新翻译面板组件 - 简化增强版
 * 提供快捷指令和自定义指令输入功能
 */

import { useState, useCallback } from 'react';
import { RefreshCw, Zap, Briefcase, MessageCircle, X } from 'lucide-react';
import { Button } from '../../../../components/ui';
import { cn } from '../../../../shared/utils';

interface RetranslatePanelProps {
  onRetranslate: (instruction: string) => Promise<void>;
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

export function RetranslatePanel({
  onRetranslate,
  isRetranslating = false,
  className,
}: RetranslatePanelProps) {
  const [customInstruction, setCustomInstruction] = useState('');
  const [selectedInstruction, setSelectedInstruction] = useState<string | null>(null);

  const handleQuickInstruction = useCallback(
    async (instruction: QuickInstruction) => {
      setSelectedInstruction(instruction.id);
      try {
        await onRetranslate(instruction.instruction);
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
          重新翻译会生成一个新的翻译版本，您可以在版本列表中选择最合适的译文。
        </p>
      </div>
    </div>
  );
}
