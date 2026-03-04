/**
 * 重翻选项模态框组件
 * 让用户选择重翻策略
 */

import { useState, useCallback, useEffect } from 'react';
import { RefreshCw, Zap, Briefcase, MessageCircle, FileText, Sparkles, Check } from 'lucide-react';
import { Modal } from '../../../../components/ui/Modal';
import { Button } from '../../../../components/ui';
import { cn } from '../../../../shared/utils';
import { confirmationApi } from '../../api/confirmationApi';

interface RetranslateOption {
  id: string;
  label: string;
  description: string;
  instruction: string;
}

interface RetranslateOptionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (instruction: string, optionId: string) => Promise<void>;
  projectId: string;
  paragraphId: string;
  isRetranslating?: boolean;
}

const iconMap: Record<string, React.ReactNode> = {
  fluent: <Sparkles className="h-5 w-5" />,
  professional: <Briefcase className="h-5 w-5" />,
  concise: <Zap className="h-5 w-5" />,
  colloquial: <MessageCircle className="h-5 w-5" />,
  literal: <FileText className="h-5 w-5" />,
  creative: <RefreshCw className="h-5 w-5" />,
};

export function RetranslateOptionsModal({
  isOpen,
  onClose,
  onSelect,
  projectId,
  paragraphId: _paragraphId,
  isRetranslating = false,
}: RetranslateOptionsModalProps) {
  const [options, setOptions] = useState<RetranslateOption[]>([]);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [customInstruction, setCustomInstruction] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useCustom, setUseCustom] = useState(false);

  const loadOptions = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await confirmationApi.getRetranslateOptions(projectId);
      setOptions(response.options || []);
    } catch (error) {
      console.error('Failed to load retranslate options:', error);
      // 使用默认选项
      setOptions([
        {
          id: 'fluent',
          label: '可读性',
          description: '消除翻译腔，优化句法结构',
          instruction: '请从句法结构层面优化译文：拆长句（控制在15-30字）、去被动语态改主动、删多余连接词、调整为中文语序、直接用动词、连续三个"的"必须拆句。'
        },
        {
          id: 'concise',
          label: '更地道',
          description: '自然流畅的中文表达',
          instruction: '请从表达层面优化译文：用具体事实代替空泛描述、用简单结构代替复杂绕行、不要公式化段落和同义词循环、把"基于""鉴于""旨在"换成自然表达。'
        },
        {
          id: 'professional',
          label: '更专业',
          description: '分析师水准，保留判断力度',
          instruction: '请优化译文的专业表达，体现semiAnalysis分析师水准：保留原文观点和判断力度不要弱化、产品/技术代号保留英文行业术语用中文、删除口水话和宣传腔、数据密集段落拆分重组。'
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  // 加载选项列表
  useEffect(() => {
    if (isOpen) {
      loadOptions();
    }
  }, [isOpen, loadOptions]);

  const handleSelectOption = useCallback((optionId: string) => {
    setSelectedOption(optionId);
    setUseCustom(false);
  }, []);

  const handleConfirm = useCallback(async () => {
    if (useCustom) {
      if (!customInstruction.trim()) return;
      await onSelect(customInstruction.trim(), 'custom');
    } else if (selectedOption) {
      const option = options.find(o => o.id === selectedOption);
      if (option) {
        await onSelect(option.instruction, option.id);
      }
    }
    onClose();
  }, [useCustom, customInstruction, selectedOption, options, onSelect, onClose]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="选择重翻策略">
      <div className="space-y-4 p-6">
        {/* 选项列表 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-primary">
            选择一个改进方向
          </label>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {options.map((option) => (
                <button
                  key={option.id}
                  onClick={() => handleSelectOption(option.id)}
                  disabled={isRetranslating}
                  className={cn(
                    'flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-all',
                    'hover:border-primary/50 hover:bg-primary/5',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    selectedOption === option.id && !useCustom
                      ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                      : 'border-border'
                  )}
                >
                  <div className="flex w-full items-center justify-between">
                    <div className={cn(
                      'rounded-lg p-2',
                      selectedOption === option.id && !useCustom
                        ? 'bg-primary text-white'
                        : 'bg-bg-hover text-text-secondary'
                    )}>
                      {iconMap[option.id] || <RefreshCw className="h-5 w-5" />}
                    </div>
                    {selectedOption === option.id && !useCustom && (
                      <Check className="h-5 w-5 text-primary" />
                    )}
                  </div>
                  <div>
                    <div className="font-medium text-text-primary">{option.label}</div>
                    <div className="mt-1 text-xs text-text-muted">{option.description}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 分隔线 */}
        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-text-muted">或</span>
          <div className="h-px flex-1 bg-border" />
        </div>

        {/* 自定义指令 */}
        <div>
          <button
            onClick={() => {
              setUseCustom(true);
              setSelectedOption(null);
            }}
            className={cn(
              'mb-2 w-full rounded-lg border p-3 text-left transition-all',
              'hover:border-primary/50',
              useCustom ? 'border-primary bg-primary/5' : 'border-border'
            )}
          >
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4 text-text-secondary" />
              <span className="text-sm font-medium text-text-primary">自定义指令</span>
            </div>
          </button>

          {useCustom && (
            <textarea
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              placeholder="输入你的翻译指令，例如：请用更通俗易懂的方式翻译..."
              className={cn(
                'w-full rounded-lg border border-border px-4 py-3',
                'bg-bg-tertiary text-text-primary text-sm',
                'focus:outline-none focus:ring-2 focus:ring-primary-500',
                'placeholder:text-text-muted',
                'min-h-[100px] resize-none'
              )}
            />
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3 pt-2">
          <Button
            variant="secondary"
            onClick={onClose}
            className="flex-1"
            disabled={isRetranslating}
          >
            取消
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            disabled={
              (!selectedOption && !useCustom) ||
              (useCustom && !customInstruction.trim()) ||
              isRetranslating
            }
            isLoading={isRetranslating}
            leftIcon={<RefreshCw className="h-4 w-4" />}
            className="flex-1"
          >
            {isRetranslating ? '翻译中...' : '开始重翻'}
          </Button>
        </div>

        {/* 提示信息 */}
        <div className="rounded-lg bg-info/10 p-3">
          <p className="text-xs text-info">
            重新翻译会生成一个新的翻译版本，您可以在版本列表中对比选择最合适的译文。
          </p>
        </div>
      </div>
    </Modal>
  );
}
