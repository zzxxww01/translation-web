/**
 * 帖子翻译功能模块
 * 同步原生 JS 版本的所有功能
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Send,
  Copy,
  Trash2,
  Sparkles,
  Wand2,
} from 'lucide-react';
import { usePostStore } from '../../shared/stores';
import { useTranslatePost, useOptimizePost, useGenerateTitle } from './hooks';
import { Button } from '../../components/ui';
import { Textarea } from '../../components/ui';
import { Modal } from '../../components/ui';
import { copyToClipboard, getCharCount } from '../../shared/utils';
import { TranslationVersionType } from '../../shared/constants';
import type { Instruction } from './types';

const quickInstructions: Instruction[] = [
  { id: 'readable', label: '可读性', icon: '✨', instruction: '' },
  { id: 'idiomatic', label: '更地道', icon: '💬', instruction: '' },
  { id: 'professional', label: '专业化', icon: '👔', instruction: '' },
  { id: 'custom', label: '自定义', icon: '🔧', instruction: '' },
];

const moreInstructions: Instruction[] = [
  { id: 'shorten', label: '精简内容', icon: '✂️', instruction: '请精简译文内容，删除冗余表达，只保留核心信息和关键观点。' },
  { id: 'expand', label: '展开说明', icon: '📖', instruction: '请对译文中的关键点添加更多解释和背景信息，使内容更丰富。' },
  { id: 'formal', label: '正式公文', icon: '📜', instruction: '请将译文重写为正式公文风格，使用规范、严谨的官方表达。' },
  { id: 'story', label: '故事化', icon: '📖', instruction: '请用叙事方式重新组织译文内容，使其更具故事性和可读性。' },
  { id: 'qa', label: 'Q&A格式', icon: '❓', instruction: '请将译文转换为问答形式，先列出问题，然后给出答案。' },
  { id: 'social', label: '社交媒体', icon: '💬', instruction: '请将译文改写为适合社交媒体传播的风格，使用轻松活泼的表达，添加emoji。' },
];

export function PostFeature() {
  const {
    originalText,
    versions,
    currentVersionId,
    isEdited,
    editedContent,
    isLoading,
    setOriginalText,
    addVersion,
    setCurrentVersion,
    setEditedContent,
    saveEdit,
    discardEdit,
    clear,
    setLoading,
  } = usePostStore();

  const translateMutation = useTranslatePost();
  const optimizeMutation = useOptimizePost();
  const generateTitleMutation = useGenerateTitle();

  // 状态
  const [customInstruction, setCustomInstruction] = useState('');
  const [titleInstruction, setTitleInstruction] = useState('');
  const [showMoreInstructions, setShowMoreInstructions] = useState(false);
  const [generatedTitles, setGeneratedTitles] = useState<string[]>([]);

  // 翻译
  const handleTranslate = useCallback(async () => {
    if (!originalText.trim()) {
      return;
    }

    setLoading(true);
    try {
      const result = await translateMutation.mutateAsync({ content: originalText });

      if (!result.translation || result.translation.trim().length === 0) {
        alert('翻译失败：服务器返回了空内容，请检查API配置或联系管理员');
        return;
      }

      addVersion(result.translation, TranslationVersionType.TRANSLATION);
      setGeneratedTitles([]); // 清空之前的标题
    } catch (error) {
      console.error('翻译失败:', error);
    } finally {
      setLoading(false);
    }
  }, [originalText, setLoading, translateMutation, addVersion]);

  // 优化
  const handleOptimize = useCallback(async (options: { instruction?: string; optionId?: string }) => {
    if (!originalText) {
      return;
    }

    const currentVersion = versions.find(v => v.id === currentVersionId);
    if (!currentVersion) {
      alert('优化失败：请先进行翻译');
      return;
    }

    setLoading(true);
    try {
      const result = await optimizeMutation.mutateAsync({
        original_text: originalText,
        current_translation: currentVersion.content,
        instruction: options.instruction,
        option_id: options.optionId,
        conversation_history: versions
          .filter(v => v.instruction)
          .slice(-3)
          .map(v => ({ role: 'user', content: v.instruction || '' })),
      });

      if (!result.optimized_translation || result.optimized_translation.trim().length === 0) {
        alert('优化失败：服务器返回了空内容，请检查API配置或联系管理员');
        return;
      }

      addVersion(
        result.optimized_translation,
        TranslationVersionType.OPTIMIZATION,
        options.optionId ? `[${options.optionId}]` : options.instruction
      );
    } catch (error) {
      console.error('优化失败:', error);
    } finally {
      setLoading(false);
    }
  }, [originalText, versions, currentVersionId, setLoading, optimizeMutation, addVersion]);

  // 快捷指令点击
  const handleQuickInstruction = (instructionKey: string) => {
    if (instructionKey === 'custom') {
      // 聚焦到自定义输入框
      document.getElementById('customInstructionInput')?.focus();
    } else {
      handleOptimize({ optionId: instructionKey });
    }
  };

  // 复制译文
  const handleCopy = async () => {
    const content = isEdited ? editedContent : versions.find(v => v.id === currentVersionId)?.content || '';
    if (content) {
      await copyToClipboard(content);
    }
  };

  // 生成标题
  const handleGenerateTitle = async () => {
    const currentVersion = versions.find(v => v.id === currentVersionId);
    const content = currentVersion?.content || editedContent || originalText;

    if (!content || content.trim().length < 50) {
      return;
    }

    setLoading(true);
    try {
      const result = await generateTitleMutation.mutateAsync({
        content,
        instruction: titleInstruction.trim() || undefined,
      });
      // 解析标题（按行分割）
      const titles = result.title.split('\n').filter(t => t.trim()).slice(0, 8);
      setGeneratedTitles(titles);
    } finally {
      setLoading(false);
    }
  };

  // 清空
  const handleClear = () => {
    setOriginalText('');
    clear();
    setGeneratedTitles([]);
    setTitleInstruction('');
  };

  // 当前版本内容
  const currentContent = isEdited ? editedContent : versions.find(v => v.id === currentVersionId)?.content || '';

  // 字符数
  const sourceCharCount = getCharCount(originalText);
  const translationCharCount = getCharCount(currentContent);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+Enter: 翻译
      if (e.ctrlKey && e.key === 'Enter') {
        const activeElement = document.activeElement as HTMLElement;
        if (activeElement?.id === 'postSourceInput') {
          e.preventDefault();
          handleTranslate();
        }
      }
        // Ctrl+K: 发送优化指令
      if (e.ctrlKey && e.key === 'k') {
        const activeElement = document.activeElement as HTMLElement;
        if (activeElement?.id === 'customInstructionInput' || activeElement?.id === 'translationEditor') {
          e.preventDefault();
          if (customInstruction.trim()) {
            handleOptimize({ instruction: customInstruction });
            setCustomInstruction('');
          } else {
            document.getElementById('customInstructionInput')?.focus();
          }
        }
      }
      // Esc: 放弃编辑
      if (e.key === 'Escape') {
        if (isEdited) {
          discardEdit();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [customInstruction, discardEdit, handleOptimize, handleTranslate, isEdited]);

  return (
    <div className="flex h-full bg-bg-primary overflow-auto">
      <div className="mx-auto w-full max-w-7xl p-6">
        {/* 标题 */}
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-text-primary">📝 帖子翻译</h2>
        </div>

        {/* 主内容区 */}
        <div className="grid grid-cols-2 gap-6">
          {/* 左侧：原文输入区 */}
          <div className="flex flex-col">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-text-primary">📄 原文</h3>
              <span className="rounded-full bg-bg-secondary px-3.5 py-1.5 text-base text-text-muted">
                {sourceCharCount} 字符
              </span>
            </div>
            <Textarea
              id="postSourceInput"
              value={originalText}
              onChange={(e) => setOriginalText(e.target.value)}
              placeholder="原文..."
              className="flex-1 min-h-[400px] text-base"
              showCharCount={false}
            />
            <div className="mt-4 flex items-center justify-between">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleClear}
                disabled={isLoading || (!originalText.trim() && versions.length === 0 && !currentContent)}
                className="px-3"
                title="清空"
              >
                <Trash2 className="mr-1.5 h-4 w-4" />
                清空
              </Button>
              <Button
                variant="primary"
                onClick={handleTranslate}
                isLoading={isLoading}
                disabled={!originalText.trim()}
                className="h-12 w-12 p-0 rounded-full hover:scale-110"
                title="翻译 (Ctrl+Enter)"
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </div>

          {/* 右侧：译文 + 优化区 */}
          <div className="flex flex-col gap-5">
            {/* 当前译文区 */}
            <div className="flex flex-1 flex-col">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-semibold text-text-primary">📝 译文</h3>
                  {/* 版本选择器 */}
                  {versions.length > 0 && (
                    <select
                      value={currentVersionId || ''}
                      onChange={(e) => setCurrentVersion(e.target.value)}
                      className="rounded-lg border border-border bg-bg-primary px-4 py-2 text-base focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">-- 选择版本 --</option>
                      {versions.map(v => {
                        const typeLabel = v.type === TranslationVersionType.TRANSLATION ? '翻译' :
                          v.type === TranslationVersionType.OPTIMIZATION ? '优化' : '编辑';
                        const instructionPreview = v.instruction
                          ? ` - ${v.instruction.substring(0, 12)}...`
                          : '';
                        return (
                          <option key={v.id} value={v.id}>
                            v{v.versionNumber} ({typeLabel}){instructionPreview}
                          </option>
                        );
                      })}
                    </select>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {isEdited && (
                    <span className="rounded-full bg-warning/10 px-2.5 py-1 text-sm font-medium text-warning">已编辑</span>
                  )}
                  <span className="rounded-full bg-bg-secondary px-3 py-1 text-sm text-text-muted">
                    {translationCharCount} 字
                  </span>
                </div>
              </div>

              <Textarea
                id="translationEditor"
                value={currentContent}
                onChange={(e) => setEditedContent(e.target.value)}
                placeholder="译文..."
                className="flex-1 min-h-[250px] text-base"
                showCharCount={false}
              />

              <div className="mt-3 flex justify-end gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleCopy}
                  disabled={!currentContent}
                  className="h-9 w-9 p-0"
                  title="复制译文"
                >
                  <Copy className="h-4 w-4" />
                </Button>
                {isEdited && (
                  <>
                    <Button variant="secondary" size="sm" onClick={discardEdit} className="px-4 py-2">
                      放弃
                    </Button>
                    <Button variant="primary" size="sm" onClick={saveEdit} className="px-4 py-2">
                      <Sparkles className="mr-1.5 h-4 w-4" />
                      保存版本
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* 优化指令区 */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5">
              <div className="mb-4 flex items-center gap-2">
                <Wand2 className="h-5 w-5 text-primary-500" />
                <h4 className="font-semibold text-text-primary">💬 优化指令</h4>
              </div>

              {/* 快捷指令标签 */}
              <div className="mb-4 flex flex-wrap gap-2.5">
                {quickInstructions.map(inst => (
                  <button
                    key={inst.id}
                    onClick={() => handleQuickInstruction(inst.id)}
                    disabled={isLoading || !originalText || versions.length === 0}
                    className="rounded-full border border-border px-5 py-2.5 text-base transition-all hover:border-primary-300 hover:bg-primary-50 disabled:opacity-40 disabled:hover:border-border disabled:hover:bg-bg-secondary"
                  >
                    {inst.icon} {inst.label}
                  </button>
                ))}
                <button
                  onClick={() => setShowMoreInstructions(true)}
                  disabled={isLoading || !originalText || versions.length === 0}
                  className="rounded-full border border-dashed border-border px-5 py-2.5 text-base text-text-muted transition-all hover:border-primary-300 hover:bg-primary-50 disabled:opacity-40"
                >
                  ⋯ 更多
                </button>
              </div>

              {/* 自定义指令输入 */}
              <div className="flex gap-2">
                <input
                  id="customInstructionInput"
                  type="text"
                  placeholder="优化要求..."
                  className="flex-1 rounded-lg border border-border bg-bg-primary px-5 py-3 text-base focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={customInstruction}
                  onChange={(e) => setCustomInstruction(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      if (customInstruction.trim()) {
                        handleOptimize({ instruction: customInstruction });
                        setCustomInstruction('');
                      }
                    }
                  }}
                  disabled={isLoading}
                />
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    if (customInstruction.trim()) {
                      handleOptimize({ instruction: customInstruction });
                      setCustomInstruction('');
                    }
                  }}
                  isLoading={isLoading}
                  disabled={versions.length === 0 || !customInstruction.trim()}
                  className="h-11 w-11 p-0 rounded-full hover:scale-110"
                  title="发送指令 (Ctrl+K)"
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>
            </div>

            {/* 生成标题区 */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary-500" />
                  <h4 className="font-semibold text-text-primary">📰 生成标题</h4>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleGenerateTitle}
                  isLoading={isLoading}
                  disabled={versions.length === 0 && !originalText}
                  className="h-8 px-3"
                >
                  ✨ 生成
                </Button>
              </div>

              <div className="mb-3">
                <input
                  type="text"
                  value={titleInstruction}
                  onChange={(e) => setTitleInstruction(e.target.value)}
                  placeholder="标题要求（可选），例如：突出“生态位”含义，语气克制"
                  className="w-full rounded-lg border border-border bg-bg-primary px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  disabled={isLoading}
                />
                <p className="mt-1 text-xs text-text-muted">
                  你可只写一两个词，系统会自动补全为完整标题生成约束 prompt。
                </p>
              </div>

              {generatedTitles.length > 0 ? (
                <div className="grid grid-cols-2 gap-2.5">
                  {generatedTitles.map((title, index) => (
                    <div
                      key={index}
                      className="group relative rounded-lg border border-border bg-bg-primary p-4 transition-all hover:border-primary-300 hover:shadow-md"
                    >
                      <div className="pr-8 text-base leading-relaxed text-text-primary">{title}</div>
                      <button
                        onClick={() => copyToClipboard(title)}
                        className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100"
                        title="复制标题"
                      >
                        📋
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center rounded-lg border border-dashed border-border bg-bg-primary py-8 text-text-muted">
                  <span className="text-sm">生成标题</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 更多指令模态框 */}
      <Modal
        isOpen={showMoreInstructions}
        onClose={() => setShowMoreInstructions(false)}
        title="更多优化指令"
      >
        <div className="grid grid-cols-2 gap-4">
          {moreInstructions.map(inst => (
            <button
              key={inst.id}
              onClick={() => {
                setShowMoreInstructions(false);
                handleOptimize({ instruction: inst.instruction });
              }}
              disabled={isLoading}
              className="flex flex-col items-center gap-3 rounded-xl border border-border bg-bg-secondary p-5 text-center transition-all hover:border-primary-300 hover:bg-primary-50 hover:shadow-md disabled:opacity-50 disabled:hover:border-border disabled:hover:bg-bg-secondary"
            >
              <span className="text-3xl">{inst.icon}</span>
              <span className="text-sm font-medium text-text-primary">{inst.label}</span>
            </button>
          ))}
        </div>
      </Modal>
    </div>
  );
}
