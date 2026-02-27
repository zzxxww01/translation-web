import { type FC, useState } from 'react';
import { Check, Copy, Edit3, X, MessageSquare } from 'lucide-react';
import { Button } from '../../../components/ui';
import { Textarea } from '../../../components/ui';
import { copyToClipboard } from '../../../shared/utils';
import { useToast } from '../../../components/ui';
import { slackApi } from '../api';

interface ReplyOption {
  label: string;
  description: string;
  content_en: string;
  content_cn: string;
}

interface ReplySuggestionsProps {
  options: ReplyOption[];
  onSelectReply: (content_en: string, content_cn: string) => void;
  onClose: () => void;
  conversationId: string;
}

/**
 * 回复建议选择组件
 * 显示3个风格选项，用户可以选择、编辑、确认使用
 * 或者输入自己的中文内容进行翻译
 */
export const ReplySuggestions: FC<ReplySuggestionsProps> = ({
  options,
  onSelectReply,
  onClose,
  conversationId,
}) => {
  const { showSuccess, showError } = useToast();
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  
  // 自定义中文输入
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customChinese, setCustomChinese] = useState('');
  const [isTranslating, setIsTranslating] = useState(false);

  const handleSelect = (index: number) => {
    setSelectedIndex(index);
    setEditedContent(options[index].content_en);
    setIsEditing(false);
    setShowCustomInput(false);
  };

  const handleCopy = async (content: string) => {
    await copyToClipboard(content);
    showSuccess('已复制到剪贴板');
  };

  const handleConfirm = () => {
    if (selectedIndex === null) return;
    const option = options[selectedIndex];
    // If edited, use edited content, otherwise use original
    const finalEn = isEditing ? editedContent : option.content_en;
    onSelectReply(finalEn, option.content_cn);
  };

  // 处理自定义中文输入 -> 翻译 -> 添加回复
  const handleCustomSubmit = async () => {
    if (!customChinese.trim()) return;
    
    setIsTranslating(true);
    try {
      const result = await slackApi.composeReply({
        content: customChinese.trim(),
        conversation_id: conversationId,
      });
      // 使用 friendly_pro 作为默认风格
      onSelectReply(result.professional, customChinese.trim());
    } catch (_error) {
      showError('翻译失败，请重试');
    } finally {
      setIsTranslating(false);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-border-subtle bg-bg-secondary p-4">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-medium text-text-primary">选择回复风格</h4>
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text-primary"
          title="跳过，不使用AI建议"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Reply options */}
      <div className="space-y-2">
        {options.map((option, index) => (
          <div
            key={index}
            onClick={() => handleSelect(index)}
            className={`cursor-pointer rounded-lg border p-3 transition-all ${
              selectedIndex === index
                ? 'border-primary-500 bg-primary-50'
                : 'border-border-subtle hover:border-border hover:bg-bg-tertiary'
            }`}
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-medium text-text-muted">
                {option.label}
              </span>
              <span className="text-xs text-text-muted">{option.description}</span>
            </div>
            <p className="text-sm text-text-primary">{option.content_en}</p>
            <p className="mt-1 text-xs text-text-muted">↳ {option.content_cn}</p>
            
            {/* Action buttons on selected */}
            {selectedIndex === index && (
              <div className="mt-2 flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopy(option.content_en);
                  }}
                >
                  <Copy className="mr-1 h-3 w-3" />
                  复制
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(!isEditing);
                  }}
                >
                  <Edit3 className="mr-1 h-3 w-3" />
                  编辑
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Edit area */}
      {isEditing && selectedIndex !== null && (
        <div className="mt-3">
          <Textarea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            placeholder="编辑回复内容..."
            className="min-h-[60px]"
            showCharCount={false}
          />
        </div>
      )}

      {/* Custom Chinese input toggle */}
      <div className="mt-3 border-t border-border-subtle pt-3">
        <button
          onClick={() => {
            setShowCustomInput(!showCustomInput);
            setSelectedIndex(null);
          }}
          className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700"
        >
          <MessageSquare className="h-4 w-4" />
          {showCustomInput ? '收起' : '或者输入我想说的中文...'}
        </button>
        
        {showCustomInput && (
          <div className="mt-2 space-y-2">
            <Textarea
              value={customChinese}
              onChange={(e) => setCustomChinese(e.target.value)}
              placeholder="输入你想表达的中文内容，AI 会翻译成地道英文..."
              className="min-h-[60px]"
              showCharCount={false}
            />
            <div className="flex justify-end">
              <Button
                variant="primary"
                size="sm"
                onClick={handleCustomSubmit}
                disabled={!customChinese.trim() || isTranslating}
                isLoading={isTranslating}
              >
                翻译并添加
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Confirm button for selected option */}
      {selectedIndex !== null && (
        <div className="mt-3 flex justify-end">
          <Button
            variant="primary"
            size="sm"
            onClick={handleConfirm}
          >
            <Check className="mr-1 h-4 w-4" />
            使用此回复
          </Button>
        </div>
      )}
    </div>
  );
};
