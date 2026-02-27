import { type FC, useState, memo } from 'react';
import { Copy, RefreshCw, Globe, Lightbulb, X } from 'lucide-react';
import type { Message, ProcessResult } from '../../../shared/types';
import { cn } from '../../../shared/utils';
import { useTranslateMessage, useGenerateReply } from '../hooks';
import { copyToClipboard } from '../../../shared/utils';
import { useSlackStore } from '../../../shared/stores';
import { useToast } from '../../../components/ui';
import { Button } from '../../../components/ui';
import { ReplySuggestions } from './ReplySuggestions';
import { slackApi } from '../api';
import { MessageRole } from '../../../shared/constants';

interface ChatBubbleProps {
  message: Message;
  index: number;
  conversationId: string;
}

export const ChatBubble: FC<ChatBubbleProps> = ({
  message,
  index,
  conversationId,
}) => {
  const translateMutation = useTranslateMessage();
  const generateReplyMutation = useGenerateReply();
  const { addMessage, updateMessage } = useSlackStore();
  const { showSuccess, showError } = useToast();

  // UI 状态
  const [isExpanded, setIsExpanded] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<ProcessResult | null>(null);

  const isMe = message.role === 'me';
  const hasTranslation = !!message.content_cn;
  const mainContent = message.content_en || message.content_cn || '';

  // 翻译
  const handleTranslate = async () => {
    if (!mainContent || isTranslating) return;
    setIsTranslating(true);
    try {
      const result = await translateMutation.mutateAsync({
        message: mainContent,
        conversation_id: conversationId,
      });
      updateMessage(index, { content_cn: result.translation });
    } catch {
      showError('翻译失败');
    } finally {
      setIsTranslating(false);
    }
  };

  // 生成回复
  const handleGenerateReply = async () => {
    if (!mainContent || isGenerating) return;
    setIsGenerating(true);
    try {
      const result = await generateReplyMutation.mutateAsync({
        message: mainContent,
        conversation_id: conversationId,
      });
      setSuggestions(result);
      setShowSuggestions(true);
    } catch {
      showError('生成失败');
    } finally {
      setIsGenerating(false);
    }
  };

  // 选择回复
  const handleSelectReply = async (content_en: string, content_cn: string) => {
    addMessage({ role: MessageRole.ME, content_en, content_cn });
    try {
      await slackApi.addMessage(conversationId, { role: MessageRole.ME, content_en, content_cn });
    } catch (error) {
      console.debug('Failed to persist selected reply:', error);
    }
    setShowSuggestions(false);
    setIsExpanded(false);
    showSuccess('回复已添加');
  };

  // 复制
  const handleCopy = async () => {
    await copyToClipboard(mainContent);
    showSuccess('已复制');
  };

  // 回复选项
  const replyOptions = suggestions ? [
    { label: '超随意', description: '像熟朋友', content_en: suggestions.super_casual, content_cn: suggestions.super_casual_cn },
    { label: '标准职场', description: '轻松专业', content_en: suggestions.friendly_pro, content_cn: suggestions.friendly_pro_cn },
    { label: '礼貌随意', description: '适合上级', content_en: suggestions.polite_casual, content_cn: suggestions.polite_casual_cn },
  ] : [];

  return (
    <div className={cn('w-full max-w-xl', isMe ? 'ml-auto' : 'mr-auto')}>
      {/* 消息气泡 - 点击展开 */}
      <div
        onClick={() => !isMe && setIsExpanded(!isExpanded)}
        className={cn(
          'rounded-2xl px-5 py-3 cursor-pointer transition-all',
          isMe ? 'bg-primary-500 text-white' : 'bg-bg-tertiary text-text-primary hover:bg-bg-tertiary/80',
          isExpanded && !isMe && 'ring-2 ring-primary-300'
        )}
      >
        {/* 主内容 */}
        <div className="whitespace-pre-wrap break-words">{mainContent}</div>

        {/* 翻译结果 - 同气泡内 */}
        {hasTranslation && (
          <div className={cn(
            'mt-3 pt-3 border-t text-base',
            isMe ? 'border-primary-400 opacity-80' : 'border-border-subtle text-text-secondary'
          )}>
            <span className="text-sm opacity-70">中文：</span>
            <span className="ml-1">{message.content_cn}</span>
          </div>
        )}
      </div>

      {/* 展开的操作面板（仅对方消息） */}
      {isExpanded && !isMe && (
        <div className="mt-2 rounded-lg border border-border-subtle bg-bg-card p-3 shadow-sm">
          {/* 关闭按钮 */}
          <div className="flex justify-end mb-2">
            <button onClick={() => setIsExpanded(false)} className="text-text-muted hover:text-text-primary">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* 操作按钮行 */}
          <div className="flex gap-2 mb-3">
            <Button
              size="sm"
              variant="secondary"
              onClick={handleTranslate}
              disabled={isTranslating}
              isLoading={isTranslating}
              className="flex-1"
            >
              <Globe className="h-5 w-5 mr-1.5" />
              {hasTranslation ? '重新翻译' : '翻译'}
              {hasTranslation && <RefreshCw className="h-4 w-4 ml-1.5" />}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleGenerateReply}
              disabled={isGenerating}
              isLoading={isGenerating}
              className="flex-1"
            >
              <Lightbulb className="h-5 w-5 mr-1.5" />
              生成回复
              {suggestions && <RefreshCw className="h-4 w-4 ml-1.5" />}
            </Button>
            <Button size="sm" variant="secondary" onClick={handleCopy}>
              <Copy className="h-5 w-5" />
            </Button>
          </div>

          {/* 回复建议 */}
          {showSuggestions && suggestions && (
            <ReplySuggestions
              options={replyOptions}
              onSelectReply={handleSelectReply}
              onClose={() => setShowSuggestions(false)}
              conversationId={conversationId}
            />
          )}
        </div>
      )}
    </div>
  );
};

// 使用 memo 优化，避免不必要的重渲染
export const MemoizedChatBubble = memo(ChatBubble);
