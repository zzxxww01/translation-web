import { toast } from 'sonner';
import { ModelSelector } from '@/components/ModelSelector';
import type { SlackReplyVariant } from '@/shared/types';
import { ConversationBubbles } from './components/ConversationBubbles';
import { ReplyWorkspace } from './components/ReplyWorkspace';
import { useComposeReply, useGenerateReply } from './hooks';
import { useSlackWorkspaceStore } from './store';

export function SlackFeature() {
  const processMutation = useGenerateReply();
  const composeMutation = useComposeReply();

  const {
    currentInput,
    currentVersions,
    isGenerating,
    conversationMessages,
    isHistoryCollapsed,
    selectedModel,
    setCurrentInput,
    setCurrentVersions,
    setGenerating,
    clearWorkspace,
    addMessage,
    removeMessage,
    updateMessage,
    clearConversation,
    toggleHistoryCollapse,
    setSelectedModel,
  } = useSlackWorkspaceStore();

  const handleGenerate = async () => {
    const input = currentInput.trim();
    if (!input) return;

    setGenerating(true);

    try {
      // 改进的中英文判断：统计中文字符占比
      const chineseChars = input.match(/[\u4e00-\u9fa5]/g) || [];
      const totalChars = input.replace(/\s/g, '').length;
      const chineseRatio = totalChars > 0 ? chineseChars.length / totalChars : 0;

      // 中文字符占比 > 30% 判断为中文输入
      const isChinese = chineseRatio > 0.3;

      if (!isChinese) {
        // 场景 1：对方发起 - 翻译并生成建议回复
        const result = await processMutation.mutateAsync({
          message: input,
          conversation_history: conversationMessages,
          model: selectedModel || undefined,
        });

        // 对方消息加入历史
        addMessage('them', input, result.translation);

        // 显示建议回复
        setCurrentVersions(result.suggested_replies ?? []);

        // 清空输入框，让用户可以输入中文调整
        setCurrentInput('');
      } else {
        // 场景 2：我发起 / 调整建议 - 中译英
        const result = await composeMutation.mutateAsync({
          content: input,
          conversation_history: conversationMessages,
          model: selectedModel || undefined,
        });

        setCurrentVersions(
          result.versions.map((v: SlackReplyVariant) => ({
            ...v,
            chinese: v.chinese || input,
          }))
        );
      }
    } catch (error) {
      toast.error('生成失败，请重试');
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectVersion = (version: SlackReplyVariant) => {
    // 加入对话历史
    addMessage('me', version.english);

    // 清空工作区
    clearWorkspace();

    toast.success('已加入对话历史');
  };

  return (
    <div className="mx-auto flex h-full w-full max-w-5xl flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Slack 回复助手</h2>
          <p className="text-sm text-muted-foreground">
            粘贴对方英文或输入中文，生成专业回复
          </p>
        </div>
        <div className="w-64">
          <label className="block text-xs text-muted-foreground mb-1.5">
            选择模型
          </label>
          <ModelSelector
            value={selectedModel}
            onChange={setSelectedModel}
            className="h-9 text-sm"
            disabled={isGenerating}
          />
        </div>
      </div>

      {/* 对话历史 */}
      <ConversationBubbles
        messages={conversationMessages}
        isCollapsed={isHistoryCollapsed}
        onToggleCollapse={toggleHistoryCollapse}
        onRemoveMessage={removeMessage}
        onUpdateMessage={updateMessage}
        onClearAll={clearConversation}
        onSelectMessage={(content) => setCurrentInput(content)}
      />

      {/* 回复工作区 */}
      <ReplyWorkspace
        currentInput={currentInput}
        currentVersions={currentVersions}
        isGenerating={isGenerating}
        onInputChange={setCurrentInput}
        onGenerate={handleGenerate}
        onSelectVersion={handleSelectVersion}
      />
    </div>
  );
}
