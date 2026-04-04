import { type FC, useEffect, useState, useCallback, useRef, type MouseEvent as ReactMouseEvent } from 'react';
import { X, RotateCw, Check, ChevronLeft, ChevronRight, Zap, MessageCircle, Briefcase, Maximize2 } from 'lucide-react';
import { useDocumentStore } from '@/shared/stores';
import { useTranslateParagraph, useConfirmParagraph, useQueryWordMeaning } from '../hooks';
import { Button } from '@/components/ui/button-extended';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { ParagraphStatus } from '@/shared/constants';
import type { Paragraph } from '@/shared/types';

interface EditPanelProps {
  paragraph: Paragraph | null;
  projectId: string | null;
  sectionId: string | null;
  onClose: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  currentIndex?: number;
  totalCount?: number;
  onEnterImmersive?: () => void;
}

type AssistantChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderInlineMarkdown(markdown: string): string {
  let html = escapeHtml(markdown);
  const codeTokens: string[] = [];

  html = html.replace(/`([^`\n]+)`/g, (_match, code) => {
    const token = `@@INLINE_CODE_${codeTokens.length}@@`;
    codeTokens.push(
      `<code class="rounded bg-bg-tertiary px-1 py-0.5 font-mono text-[0.92em]">${code}</code>`
    );
    return token;
  });

  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-primary-600 underline">$1</a>'
  );

  codeTokens.forEach((tokenHtml, index) => {
    html = html.replace(`@@INLINE_CODE_${index}@@`, tokenHtml);
  });

  return html;
}

function markdownToSafeHtml(markdown: string): string {
  const normalized = markdown.replace(/\r\n/g, '\n');
  const blockTokens: string[] = [];

  const text = normalized.replace(/```([\w-]+)?\n([\s\S]*?)```/g, (_match, lang, code) => {
    const token = `@@BLOCK_CODE_${blockTokens.length}@@`;
    const langLabel = lang
      ? `<div class="mb-1 text-xs text-text-muted">${escapeHtml(String(lang))}</div>`
      : '';
    const codeHtml = escapeHtml(String(code).trimEnd());
    blockTokens.push(
      `<div class="my-2 rounded border border-border-subtle bg-bg-tertiary p-2">${langLabel}<pre class="whitespace-pre-wrap font-mono text-xs leading-5">${codeHtml}</pre></div>`
    );
    return token;
  });

  const lines = text.split('\n');
  const parts: string[] = [];
  let inUl = false;
  let inOl = false;

  const closeLists = () => {
    if (inUl) {
      parts.push('</ul>');
      inUl = false;
    }
    if (inOl) {
      parts.push('</ol>');
      inOl = false;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      closeLists();
      parts.push('<div class="h-2"></div>');
      continue;
    }

    if (/^@@BLOCK_CODE_\d+@@$/.test(line)) {
      closeLists();
      parts.push(line);
      continue;
    }

    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      if (!inUl) {
        if (inOl) {
          parts.push('</ol>');
          inOl = false;
        }
        parts.push('<ul class="list-disc space-y-1 pl-5">');
        inUl = true;
      }
      parts.push(`<li>${renderInlineMarkdown(unordered[1])}</li>`);
      continue;
    }

    const ordered = line.match(/^\d+\.\s+(.+)$/);
    if (ordered) {
      if (!inOl) {
        if (inUl) {
          parts.push('</ul>');
          inUl = false;
        }
        parts.push('<ol class="list-decimal space-y-1 pl-5">');
        inOl = true;
      }
      parts.push(`<li>${renderInlineMarkdown(ordered[1])}</li>`);
      continue;
    }

    closeLists();

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const tag = level === 1 ? 'h1' : level === 2 ? 'h2' : 'h3';
      const sizeClass = level === 1 ? 'text-base font-bold' : level === 2 ? 'text-sm font-semibold' : 'text-sm font-medium';
      parts.push(`<${tag} class="my-1 ${sizeClass}">${renderInlineMarkdown(heading[2])}</${tag}>`);
      continue;
    }

    parts.push(`<p class="whitespace-pre-wrap">${renderInlineMarkdown(line)}</p>`);
  }

  closeLists();

  let html = parts.join('');
  blockTokens.forEach((tokenHtml, index) => {
    html = html.replace(`@@BLOCK_CODE_${index}@@`, tokenHtml);
  });
  return html;
}

export const EditPanel: FC<EditPanelProps> = ({
  paragraph,
  projectId,
  sectionId,
  onClose,
  onNext,
  onPrev,
  currentIndex = 0,
  totalCount = 0,
  onEnterImmersive,
}) => {
  const { updateParagraph } = useDocumentStore();
  const translateMutation = useTranslateParagraph();
  const confirmMutation = useConfirmParagraph();
  const queryWordMeaningMutation = useQueryWordMeaning();
  const [translation, setTranslation] = useState(paragraph?.translation || '');
  const [isTranslating, setIsTranslating] = useState(false);

  // 重新翻译选项
  const [customRetranslateInstruction, setCustomRetranslateInstruction] = useState('');

  const sourceSelectionContainerRef = useRef<HTMLDivElement | null>(null);
  const assistantBottomRef = useRef<HTMLDivElement | null>(null);
  const lastSelectedWordRef = useRef('');
  const lastSelectedAtRef = useRef(0);

  // 词义助手相关状态
  const [selectedWord, setSelectedWord] = useState('');
  const [activeWord, setActiveWord] = useState('');
  const [isWordAssistantOpen, setIsWordAssistantOpen] = useState(false);
  const [assistantMessages, setAssistantMessages] = useState<AssistantChatMessage[]>([]);
  const [assistantInput, setAssistantInput] = useState('');
  const [isAskingWordMeaning, setIsAskingWordMeaning] = useState(false);
  const [wordMenuPosition, setWordMenuPosition] = useState<{ x: number; y: number } | null>(null);

  // 快捷指令
  const quickInstructions = [
    {
      id: 'readable',
      label: '可读性',
      icon: <Zap className="h-3 w-3" />,
      instruction:
        '请提升可读性：拆分过长句，优化语序，减少冗余连接词，保持信息完整和逻辑清晰。',
    },
    {
      id: 'professional',
      label: '专业化',
      icon: <Briefcase className="h-3 w-3" />,
      instruction:
        '请提升专业表达：术语更准确、行业表述更规范，保留技术细节和判断力度。',
    },
    {
      id: 'idiomatic',
      label: '更地道',
      icon: <MessageCircle className="h-3 w-3" />,
      instruction:
        '请使中文更地道自然：避免翻译腔，改为符合中文读者习惯的表达，但不改变原意。',
    },
  ];

  useEffect(() => {
    setTranslation(paragraph?.translation || '');
    setSelectedWord('');
    setActiveWord('');
    setIsWordAssistantOpen(false);
    setAssistantMessages([]);
    setAssistantInput('');
    setIsAskingWordMeaning(false);
    setWordMenuPosition(null);
    setCustomRetranslateInstruction('');
    lastSelectedWordRef.current = '';
    lastSelectedAtRef.current = 0;
  }, [paragraph]);

  const closeWordAssistant = useCallback(() => {
    setIsWordAssistantOpen(false);
    setAssistantInput('');
  }, []);

  const closeWordMenu = useCallback(() => {
    setWordMenuPosition(null);
  }, []);

  const handleTranslate = useCallback(async (instruction?: string) => {
    if (!projectId || !sectionId || !paragraph) return;

    setIsTranslating(true);
    try {
      const result = await translateMutation.mutateAsync({
        projectId,
        sectionId,
        paragraphId: paragraph.id,
        instruction,
      });
      setTranslation(result.translation);
      const persistedStatus = result.status ?? ParagraphStatus.TRANSLATED;
      updateParagraph(paragraph.id, {
        translation: result.translation,
        status: persistedStatus,
        confirmed:
          result.confirmed ?? (persistedStatus === ParagraphStatus.APPROVED ? result.translation : undefined),
      });
    } finally {
      setIsTranslating(false);
    }
  }, [projectId, sectionId, paragraph, translateMutation, updateParagraph]);

  const handleCustomRetranslate = useCallback(() => {
    const instruction = customRetranslateInstruction.trim();
    if (!instruction || isTranslating) return;
    setCustomRetranslateInstruction('');
    void handleTranslate(instruction);
  }, [customRetranslateInstruction, handleTranslate, isTranslating]);

  const handleConfirm = useCallback(async () => {
    if (!translation.trim()) {
      return;
    }
    if (!projectId || !sectionId || !paragraph) return;

    await confirmMutation.mutateAsync({
      projectId,
      sectionId,
      paragraphId: paragraph.id,
      translation,
    });

    updateParagraph(paragraph.id, {
      translation,
      status: ParagraphStatus.APPROVED,
      confirmed: translation,
    });

    if (onNext) {
      onNext();
    }
  }, [translation, projectId, sectionId, paragraph, confirmMutation, updateParagraph, onNext]);

  const getSelectedSourceText = useCallback(() => {
    const container = sourceSelectionContainerRef.current;
    if (!container) return '';

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return '';

    const anchorNode = selection.anchorNode;
    const focusNode = selection.focusNode;
    if (!anchorNode || !focusNode) return '';
    if (!container.contains(anchorNode) || !container.contains(focusNode)) return '';

    return selection.toString().trim().replace(/\s+/g, ' ');
  }, []);

  const handleSourceSelection = useCallback(() => {
    const selected = getSelectedSourceText();
    if (!selected) {
      setSelectedWord('');
      setWordMenuPosition(null);
      return;
    }
    setSelectedWord(selected);
    lastSelectedWordRef.current = selected;
    lastSelectedAtRef.current = Date.now();
    setWordMenuPosition(null);
  }, [getSelectedSourceText]);

  const handleSourceContextMenu = useCallback((e: ReactMouseEvent<HTMLDivElement>) => {
    const selectedNow = getSelectedSourceText();
    const useRecentSelection = Date.now() - lastSelectedAtRef.current <= 2000;
    const selected = selectedNow || (useRecentSelection ? lastSelectedWordRef.current : '');
    if (!selected) {
      setSelectedWord('');
      setWordMenuPosition(null);
      return;
    }

    e.preventDefault();
    e.stopPropagation();
    setSelectedWord(selected);
    lastSelectedWordRef.current = selected;

    const menuWidth = 240;
    const menuHeight = 52;
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 12);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 12);
    setWordMenuPosition({ x, y });
  }, [getSelectedSourceText]);

  const askWordMeaning = useCallback(
    async (question: string, word: string, baseHistory: AssistantChatMessage[]) => {
      if (!projectId || !sectionId || !paragraph) return;

      const trimmedQuestion = question.trim();
      const trimmedWord = word.trim();
      if (!trimmedQuestion || !trimmedWord) return;

      const nextHistory: AssistantChatMessage[] = [
        ...baseHistory,
        { role: 'user', content: trimmedQuestion },
      ];
      setAssistantMessages(nextHistory);
      setIsAskingWordMeaning(true);

      try {
        const result = await queryWordMeaningMutation.mutateAsync({
          projectId,
          sectionId,
          paragraphId: paragraph.id,
          word: trimmedWord,
          query: trimmedQuestion,
          history: nextHistory,
        });

        setAssistantMessages([
          ...nextHistory,
          { role: 'assistant', content: result.answer },
        ]);
      } finally {
        setIsAskingWordMeaning(false);
      }
    },
    [projectId, sectionId, paragraph, queryWordMeaningMutation]
  );

  const handleLookupWordMeaning = useCallback(() => {
    const word = selectedWord.trim();
    if (!word) return;

    setActiveWord(word);
    setIsWordAssistantOpen(true);
    setSelectedWord('');
    setWordMenuPosition(null);
    lastSelectedWordRef.current = '';
    lastSelectedAtRef.current = 0;
    setAssistantMessages([]);
    setAssistantInput('');

    void askWordMeaning(`${word}是什么意思`, word, []);
  }, [selectedWord, askWordMeaning]);

  const handleSendAssistantMessage = useCallback(() => {
    const question = assistantInput.trim();
    if (!question || !activeWord || isAskingWordMeaning) return;

    setAssistantInput('');
    void askWordMeaning(question, activeWord, assistantMessages);
  }, [assistantInput, activeWord, isAskingWordMeaning, askWordMeaning, assistantMessages]);

  useEffect(() => {
    if (!isWordAssistantOpen) return;
    assistantBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [assistantMessages, isAskingWordMeaning, isWordAssistantOpen]);

  useEffect(() => {
    if (!wordMenuPosition) return;

    const handleWindowClick = () => {
      setWordMenuPosition(null);
    };
    const handleWindowResize = () => {
      setWordMenuPosition(null);
    };

    window.addEventListener('click', handleWindowClick);
    window.addEventListener('resize', handleWindowResize);
    window.addEventListener('scroll', handleWindowResize, true);
    return () => {
      window.removeEventListener('click', handleWindowClick);
      window.removeEventListener('resize', handleWindowResize);
      window.removeEventListener('scroll', handleWindowResize, true);
    };
  }, [wordMenuPosition]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!paragraph) return;

      // Ctrl+T: 翻译
      if (e.ctrlKey && e.key === 't') {
        e.preventDefault();
        handleTranslate();
      }
      // Ctrl+Enter: 确认并下一段
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        handleConfirm();
      }
      // Ctrl+左箭头: 上一段
      if (e.ctrlKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        onPrev?.();
      }
      // Ctrl+右箭头: 下一段
      if (e.ctrlKey && e.key === 'ArrowRight') {
        e.preventDefault();
        onNext?.();
      }
      // Escape: 关闭
      if (e.key === 'Escape') {
        e.preventDefault();
        if (wordMenuPosition) {
          closeWordMenu();
          return;
        }
        if (isWordAssistantOpen) {
          closeWordAssistant();
          return;
        }
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    paragraph,
    handleTranslate,
    handleConfirm,
    onNext,
    onPrev,
    onClose,
    isWordAssistantOpen,
    closeWordAssistant,
    wordMenuPosition,
    closeWordMenu,
  ]);

  if (!paragraph) return null;
  const elementType = paragraph.element_type ?? 'p';

  const renderSource = () => {
    if (elementType === 'image') {
      return (
        <img
          src={paragraph.source}
          alt="image"
          className="max-h-96 w-auto rounded border border-border-subtle bg-bg-tertiary object-contain"
          loading="lazy"
        />
      );
    }
    if (elementType === 'table' && paragraph.source_html) {
      return (
        <div
          className="max-h-[28rem] overflow-auto rounded border border-border-subtle bg-bg-tertiary p-3 text-sm"
          dangerouslySetInnerHTML={{ __html: paragraph.source_html }}
        />
      );
    }
    if (elementType === 'code') {
      return (
        <pre className="whitespace-pre-wrap rounded border border-border-subtle bg-bg-tertiary p-3 text-sm">
          {paragraph.source}
        </pre>
      );
    }
    return <span>{paragraph.source}</span>;
  };

  const isLoading = isTranslating || translateMutation.isPending || confirmMutation.isPending;

  return (
    <>
      {/* 背景遮罩 */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
      />

      {/* 编辑面板 - 居中大弹窗 */}
      <div className="fixed inset-4 z-50 flex items-center justify-center md:inset-8 lg:inset-16">
        <div className="flex h-full w-full max-w-5xl flex-col rounded-xl bg-bg-primary shadow-2xl">
          {/* 头部 */}
          <div className="flex items-center justify-between border-b border-border-subtle px-6 py-4">
            <div className="flex items-center gap-4">
              <h3 className="text-xl font-semibold">编辑译文</h3>
              <span className="text-lg text-text-muted">
                第 {currentIndex + 1} 段 / 共 {totalCount} 段
              </span>
            </div>

            {/* 导航按钮 */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="default"
                onClick={onPrev}
                disabled={currentIndex <= 0 || isLoading}
                leftIcon={<ChevronLeft className="h-5 w-5" />}
              >
                上一段
              </Button>
              <Button
                variant="outline"
                size="default"
                onClick={onNext}
                disabled={currentIndex >= totalCount - 1 || isLoading}
                rightIcon={<ChevronRight className="h-5 w-5" />}
              >
                下一段
              </Button>
              {onEnterImmersive && (
                <>
                  <div className="mx-2 h-8 w-px bg-border-subtle" />
                  <Button
                    variant="outline"
                    size="default"
                    onClick={onEnterImmersive}
                    leftIcon={<Maximize2 className="h-4 w-4" />}
                  >
                    沉浸编辑
                  </Button>
                </>
              )}
              <div className="mx-3 h-8 w-px bg-border-subtle" />
              <button
                onClick={onClose}
                className="rounded p-2.5 text-text-muted transition-colors hover:text-text-primary hover:bg-bg-tertiary"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>

          {/* 主内容区 - 左右分栏 */}
          <div className="flex flex-1 overflow-hidden">
            {/* 左侧：原文 */}
            <div className="flex w-1/2 flex-col border-r border-border-subtle p-6">
              <label className="mb-3 block text-lg font-semibold text-text-primary">
                原文
              </label>
              <p className="mb-2 text-xs text-text-muted">
                划词翻译
              </p>
              <div
                ref={sourceSelectionContainerRef}
                onMouseUp={handleSourceSelection}
                onKeyUp={handleSourceSelection}
                onContextMenu={handleSourceContextMenu}
                className="flex-1 overflow-auto rounded-lg bg-bg-secondary p-4 text-lg leading-7 text-text-primary"
              >
                {renderSource()}
              </div>
            </div>

            {/* 右侧：译文编辑 */}
            <div className="flex w-1/2 flex-col p-6">
              <label className="mb-3 block text-lg font-semibold text-text-primary">
                译文
              </label>
              <textarea
                value={translation}
                onChange={(e) => {
                  setTranslation(e.target.value);
                }}
                placeholder="在此输入或编辑译文..."
                className="flex-1 w-full resize-none rounded-lg border border-border bg-bg-secondary p-4 text-lg leading-7 text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* 底部操作栏 */}
          <div className="border-t border-border-subtle px-6 py-4">
            <div className="flex items-center justify-between">
              {/* 快捷键提示和模型选择 */}
              <div className="flex items-center gap-6">
                <div className="flex gap-4 text-sm text-text-muted">
                  <span>Ctrl+T 翻译</span>
                  <span>Ctrl+Enter 确认</span>
                  <span>Esc 关闭</span>
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-3 items-center">
                {/* 翻译/重新翻译按钮组 */}
                {paragraph.translation ? (
                  <DropdownMenu>
                    <div className="flex">
                      <Button
                        variant="outline"
                        onClick={() => handleTranslate()}
                        isLoading={isTranslating}
                        disabled={isLoading}
                        leftIcon={<RotateCw className="h-5 w-5" />}
                        className="rounded-r-none border-r-0"
                      >
                        重新翻译
                      </Button>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="outline"
                          size="icon"
                          disabled={isLoading}
                          className="rounded-l-none"
                        >
                          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M6 9l6 6 6-6" />
                          </svg>
                        </Button>
                      </DropdownMenuTrigger>
                    </div>
                    <DropdownMenuContent align="end" className="w-80">
                      <DropdownMenuLabel>快捷指令</DropdownMenuLabel>
                      {quickInstructions.map((item) => (
                        <DropdownMenuItem
                          key={item.id}
                          onClick={() => handleTranslate(item.instruction)}
                          disabled={isTranslating}
                        >
                          {item.icon}
                          <span>{item.label}</span>
                        </DropdownMenuItem>
                      ))}
                      <DropdownMenuSeparator />
                      <div className="p-2">
                        <div className="px-1 py-1 text-xs text-text-muted font-medium">手动输入</div>
                        <textarea
                          value={customRetranslateInstruction}
                          onChange={event => setCustomRetranslateInstruction(event.target.value)}
                          placeholder={'输入重译要求（例如：保留"生态位"含义，语气更克制）'}
                          className="h-20 w-full resize-none rounded border border-border-subtle bg-bg-secondary px-2 py-1.5 text-sm text-text-primary outline-none focus:border-primary-500"
                          disabled={isTranslating}
                          onClick={(e) => e.stopPropagation()}
                          onKeyDown={(e) => e.stopPropagation()}
                        />
                        <div className="mt-2 flex justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCustomRetranslate();
                            }}
                            disabled={!customRetranslateInstruction.trim() || isTranslating}
                          >
                            发送并重译
                          </Button>
                        </div>
                      </div>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => handleTranslate()}
                    isLoading={isTranslating}
                    disabled={isLoading}
                    leftIcon={<RotateCw className="h-5 w-5" />}
                  >
                    翻译
                  </Button>
                )}

                <Button
                  variant="default"
                  onClick={handleConfirm}
                  disabled={!translation.trim() || isLoading}
                  isLoading={confirmMutation.isPending}
                  leftIcon={<Check className="h-5 w-5" />}
                >
                  确认并下一段
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 原文选词右键菜单 */}
      {wordMenuPosition && selectedWord && !isWordAssistantOpen && (
        <div
          className="fixed z-[55]"
          style={{ left: `${wordMenuPosition.x}px`, top: `${wordMenuPosition.y}px` }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={handleLookupWordMeaning}
            disabled={isLoading || isAskingWordMeaning}
            className="rounded-lg border border-border-subtle bg-bg-primary px-3 py-2 text-sm text-text-primary shadow-xl transition-colors hover:bg-bg-secondary disabled:opacity-50"
          >
            查询"{selectedWord.length > 24 ? `${selectedWord.slice(0, 24)}...` : selectedWord}"的意思
          </button>
        </div>
      )}

      {/* 词义助手弹窗 */}
      <Dialog open={isWordAssistantOpen} onOpenChange={(open) => { if (!open) closeWordAssistant(); }}>
        <DialogContent className="sm:max-w-[760px]">
          <DialogHeader>
            <DialogTitle>词义助手</DialogTitle>
            <DialogDescription>
              当前词语：{activeWord}
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-[46vh] min-h-[260px] space-y-3 overflow-auto">
            {assistantMessages.length === 0 && !isAskingWordMeaning && (
              <div className="rounded-lg bg-bg-secondary px-3 py-2 text-sm text-text-muted">
                选中词语后将自动提问"xxx是什么意思"，你也可以继续追问语境、词性和用法。
              </div>
            )}

            {assistantMessages.map((message, index) => (
              <div
                key={`word-assistant-${index}`}
                className={
                  message.role === 'user'
                    ? 'ml-12 rounded-lg bg-primary-50 px-3 py-2 text-sm leading-6 text-text-primary'
                    : 'mr-12 rounded-lg bg-bg-secondary px-3 py-2 text-sm leading-6 text-text-primary'
                }
              >
                <div className="mb-1 text-xs text-text-muted">
                  {message.role === 'user' ? '你' : '词义助手'}
                </div>
                {message.role === 'assistant' ? (
                  <div
                    className="space-y-1 text-sm leading-6"
                    dangerouslySetInnerHTML={{ __html: markdownToSafeHtml(message.content) }}
                  />
                ) : (
                  <div className="whitespace-pre-wrap">{message.content}</div>
                )}
              </div>
            ))}

            {isAskingWordMeaning && (
              <div className="mr-12 rounded-lg bg-bg-secondary px-3 py-2 text-sm text-text-muted">
                正在思考...
              </div>
            )}

            <div ref={assistantBottomRef} />
          </div>

          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={assistantInput}
                onChange={(e) => setAssistantInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendAssistantMessage();
                  }
                }}
                placeholder="继续追问，例如：这个词在这里是褒义还是中性？"
                className="h-11 flex-1 rounded-lg border border-border bg-bg-secondary px-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <Button
                variant="default"
                onClick={handleSendAssistantMessage}
                disabled={!assistantInput.trim() || isAskingWordMeaning}
                isLoading={isAskingWordMeaning}
              >
                发送
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
