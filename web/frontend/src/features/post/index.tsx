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

/**
 * 优化指令模板（与原生 JS 版本一致）
 */
const instructionTemplates: Record<string, string> = {
  readable: `请从句法结构层面优化译文，消除翻译腔：
1. 拆长句：超过30字的句子拆成2-3个短句，中文句子控制在15-30字
2. 去被动：被动语态一律改为主动表达
3. 减连接词：删掉多余的"此外""然而""值得注意的是"，中文靠语义衔接
4. 调语序：条件、原因、时间状语放到句首，按中文思维重新组织
5. 用动词：把"对……进行……""做出了……"改为直接动词
6. 消除"的"堆砌：连续出现三个"的"必须拆句重组`,

  idiomatic: `请从表达层面优化译文，让中文更地道自然：
1. 用具体数据和事实替代空泛描述，删掉"突破性""革命性"等宣传词
2. 用简单结构（是/有/能）代替复杂绕行（"作为……的体现""充当……的角色"）
3. 不要公式化段落（"尽管……但仍……""展望未来""综上所述"）
4. 不要同义词循环替换，同一个概念前后用同一个词
5. 模糊归因要么给出具体来源，要么删掉（不要"业界专家普遍认为"）
6. 口语化替换：把"基于""鉴于""旨在"换成"根据""考虑到""为了"等自然表达`,

  professional: `请优化译文的专业表达，使其体现semiAnalysis的分析师水准：
1. 保留原文的观点和判断力度，不要弱化成中性表述（"We believe" → "我们认为"，不是"据分析"）
2. 使用标准的半导体/科技术语，产品代号保留英文（CoWoS、HBM、EUV），行业术语用中文（晶圆代工、良率、制程节点），金融术语用中文（营收、毛利率、资本支出）
3. 删除口水话：去掉不提供信息的形容词和空洞的总结性段落
4. 不要宣传腔（"令人兴奋""开创性""无缝集成"），也不要黑话和圈子用语
5. 每句话都要有实质内容，没有信息量的句子直接删掉
6. 数据密集段落：一句话超过3个数据点拆成多句，金额统一为"亿美元"格式`,
};

const quickInstructions: Instruction[] = [
  { id: 'readable', label: '可读性', icon: '✨', instruction: instructionTemplates.readable },
  { id: 'idiomatic', label: '更地道', icon: '💬', instruction: instructionTemplates.idiomatic },
  { id: 'professional', label: '专业化', icon: '👔', instruction: instructionTemplates.professional },
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

const buildOptimizeInstruction = (
  instruction: string,
  original: string,
  currentTranslation: string,
) => `【原文】\n${original}\n\n【当前译文】\n${currentTranslation}\n\n【优化要求】\n${instruction}\n\n【固定要求】\n1. 以【原文】为准对照校对，发现与原文不一致或错误之处必须纠正。\n2. 基于原文重写，不是仅润色中文。\n3. 保留semiAnalysis的分析师语气：原文的观点、判断、锐度不要弱化。\n4. 消除翻译腔：拆长句、去被动、减连接词、调整中文语序、直接用动词。\n5. 术语处理：产品/技术代号保留英文，行业术语和金融术语用中文通用译法。\n6. 译文不要比原文更长，不要口水话、不要宣传腔。\n7. 不要使用任何 Markdown 标签或格式。\n\n请在不遗漏信息、不改变事实的前提下，根据优化要求重写译文。仅输出优化后的完整译文。`;

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
  const handleOptimize = useCallback(async (instruction: string) => {
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
      const formattedInstruction = buildOptimizeInstruction(
        instruction,
        originalText,
        currentVersion.content,
      );
      const result = await optimizeMutation.mutateAsync({
        original_text: originalText,
        current_translation: currentVersion.content,
        instruction: formattedInstruction,
        conversation_history: versions
          .filter(v => v.instruction)
          .slice(-3)
          .map(v => ({ role: 'user', content: v.instruction || '' })),
      });

      if (!result.optimized_translation || result.optimized_translation.trim().length === 0) {
        alert('优化失败：服务器返回了空内容，请检查API配置或联系管理员');
        return;
      }

      addVersion(result.optimized_translation, TranslationVersionType.OPTIMIZATION, instruction);
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
      const instruction = instructionTemplates[instructionKey];
      if (instruction) {
        handleOptimize(instruction);
      }
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
      const result = await generateTitleMutation.mutateAsync({ content });
      // 解析标题（按行分割）
      const titles = result.title.split('\n').filter(t => t.trim()).slice(0, 6);
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
            handleOptimize(customInstruction);
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
                        handleOptimize(customInstruction);
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
                      handleOptimize(customInstruction);
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
                handleOptimize(inst.instruction);
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
