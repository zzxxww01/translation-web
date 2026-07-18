import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { usePostStore } from '@/shared/stores';
import { useTranslatePost, useOptimizePost, useGenerateTitle } from './hooks';
import { TranslationVersionType } from '@/shared/constants';
import { SourceInput } from './components/SourceInput';
import { TranslationOutput } from './components/TranslationOutput';
import { OptimizationPanel } from './components/OptimizationPanel';
import { TitleGenerator } from './components/TitleGenerator';
import { ModelSelector } from '@/components/ModelSelector';
import { POST_CONTENT_MAX_LENGTH } from './types';
import { getOptimizationHistory } from './versionLineage';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

type NetworkAction = 'translate' | 'optimize' | 'title';
type PendingEditAction =
  | { kind: 'switch-version'; versionId: string }
  | { kind: 'clear' }
  | { kind: 'discard-edit' };

export function PostFeature() {
  const {
    originalText, sourceRevision, versions, currentVersionId, isEdited, editedContent, isLoading,
    selectedModel,
    setOriginalText, addVersion, setCurrentVersion, setEditedContent,
    saveEdit, discardEdit, clear, setLoading, setSelectedModel,
  } = usePostStore();

  const translateMutation = useTranslatePost();
  const optimizeMutation = useOptimizePost();
  const generateTitleMutation = useGenerateTitle();
  const [customInstruction, setCustomInstruction] = useState('');
  const [pendingAction, setPendingAction] = useState<NetworkAction | null>(null);
  const [pendingEditAction, setPendingEditAction] = useState<PendingEditAction | null>(null);
  const activeActionRef = useRef<NetworkAction | null>(null);

  const currentVersion = versions.find(v => v.id === currentVersionId);
  const currentContent = isEdited ? editedContent : currentVersion?.content || '';
  const titleContent = currentContent.trim() ? currentContent : originalText;
  const titleContentIdentity = currentVersionId
    ? `version:${currentVersionId}:${currentContent}`
    : `source:${sourceRevision}:${originalText}`;

  const beginAction = useCallback((action: NetworkAction) => {
    if (activeActionRef.current) return false;
    activeActionRef.current = action;
    setLoading(true);
    setPendingAction(action);
    return true;
  }, [setLoading]);

  const finishAction = useCallback((action: NetworkAction) => {
    if (activeActionRef.current !== action) return;
    activeActionRef.current = null;
    setLoading(false);
    setPendingAction(null);
  }, [setLoading]);

  const preserveCurrentEdit = useCallback(() => {
    if (!usePostStore.getState().isEdited) return null;
    const versionId = saveEdit();
    if (versionId) toast.info('未保存的译文已另存为手工版本');
    return versionId;
  }, [saveEdit]);

  const handleTranslate = useCallback(async (): Promise<boolean> => {
    const sourceText = originalText;
    const requestSourceRevision = sourceRevision;
    if (!sourceText.trim() || !beginAction('translate')) return false;
    preserveCurrentEdit();
    try {
      const result = await translateMutation.mutateAsync({
        content: sourceText,
        model: selectedModel,
      });
      if (!result.translation?.trim()) {
        toast.error('翻译失败：服务器返回了空内容');
        return false;
      }

      const latest = usePostStore.getState();
      if (
        latest.sourceRevision !== requestSourceRevision ||
        latest.originalText !== sourceText
      ) {
        toast.info('原文已更新，本次旧译文结果未写入版本记录');
        return false;
      }

      addVersion(result.translation, TranslationVersionType.TRANSLATION, undefined, {
        sourceRevision: requestSourceRevision,
        sourceText,
      });
      toast.success('翻译完成');
      return true;
    } catch (error) {
      console.error('翻译失败:', error);
      return false;
    } finally {
      finishAction('translate');
    }
  }, [
    addVersion,
    beginAction,
    finishAction,
    originalText,
    preserveCurrentEdit,
    selectedModel,
    sourceRevision,
    translateMutation,
  ]);

  const handleOptimize = useCallback(async (
    options: { instruction?: string; optionId?: string }
  ): Promise<boolean> => {
    const activeVersion = versions.find(v => v.id === currentVersionId);
    const translationAtStart = currentContent;
    if (!activeVersion || !translationAtStart.trim()) {
      toast.error('请先进行翻译');
      return false;
    }
    if (translationAtStart.length > POST_CONTENT_MAX_LENGTH) {
      toast.error(`译文超过 ${POST_CONTENT_MAX_LENGTH.toLocaleString()} 字符，请精简后再优化`);
      return false;
    }
    if (!beginAction('optimize')) return false;

    const savedEditVersionId = preserveCurrentEdit();
    const baseVersionId = savedEditVersionId ?? activeVersion.id;
    const stateAfterPreserve = usePostStore.getState();
    const baseVersion = stateAfterPreserve.versions.find(v => v.id === baseVersionId);
    if (!baseVersion) {
      finishAction('optimize');
      return false;
    }
    const baseSourceText = baseVersion.sourceText.trim()
      ? baseVersion.sourceText
      : stateAfterPreserve.originalText;
    const baseSourceRevision = baseVersion.sourceText.trim()
      ? baseVersion.sourceRevision
      : stateAfterPreserve.sourceRevision;
    if (!baseSourceText.trim()) {
      finishAction('optimize');
      toast.error('缺少对应原文，无法优化译文');
      return false;
    }

    const history = getOptimizationHistory(
      stateAfterPreserve.versions,
      baseVersionId,
      3
    );

    try {
      const result = await optimizeMutation.mutateAsync({
        original_text: baseSourceText,
        current_translation: translationAtStart,
        instruction: options.instruction,
        option_id: options.optionId,
        conversation_history: history,
        model: selectedModel,
      });
      if (!result.optimized_translation?.trim()) {
        toast.error('优化失败：服务器返回了空内容');
        return false;
      }

      const latest = usePostStore.getState();
      const latestBaseVersion = latest.versions.find(v => v.id === baseVersionId);
      if (
        latest.currentVersionId !== baseVersionId ||
        latest.isEdited ||
        latestBaseVersion?.content !== translationAtStart
      ) {
        toast.info('译文已更新，本次旧优化结果未写入版本记录');
        return false;
      }

      addVersion(
        result.optimized_translation,
        TranslationVersionType.OPTIMIZATION,
        options.optionId ? `[${options.optionId}]` : options.instruction,
        {
          sourceRevision: baseSourceRevision,
          sourceText: baseSourceText,
          parentVersionId: baseVersionId,
        }
      );
      toast.success('优化完成');
      return true;
    } catch (error) {
      console.error('优化失败:', error);
      return false;
    } finally {
      finishAction('optimize');
    }
  }, [
    addVersion,
    beginAction,
    currentContent,
    currentVersionId,
    finishAction,
    optimizeMutation,
    preserveCurrentEdit,
    selectedModel,
    versions,
  ]);

  const handleGenerateTitle = useCallback(async (instruction?: string): Promise<string[]> => {
    const content = titleContent;
    const contentIdentity = titleContentIdentity;
    if (!content || content.trim().length < 50) {
      toast.warning('内容过短，至少需要 50 字才能生成标题');
      return [];
    }
    if (content.length > POST_CONTENT_MAX_LENGTH) {
      toast.error(`内容超过 ${POST_CONTENT_MAX_LENGTH.toLocaleString()} 字符，请精简后再生成标题`);
      return [];
    }
    if (!beginAction('title')) return [];

    try {
      const result = await generateTitleMutation.mutateAsync({
        content,
        instruction: instruction || undefined,
        model: selectedModel,
      });

      const latest = usePostStore.getState();
      const latestVersion = latest.versions.find(v => v.id === latest.currentVersionId);
      const latestCurrentContent = latest.isEdited
        ? latest.editedContent
        : latestVersion?.content || '';
      const latestTitleContent = latestCurrentContent.trim()
        ? latestCurrentContent
        : latest.originalText;
      const latestIdentity = latest.currentVersionId
        ? `version:${latest.currentVersionId}:${latestCurrentContent}`
        : `source:${latest.sourceRevision}:${latest.originalText}`;
      if (latestIdentity !== contentIdentity || latestTitleContent !== content) {
        toast.info('内容已更新，本次旧标题结果已忽略');
        return [];
      }

      const titles = result.title.split('\n').filter((t: string) => t.trim()).slice(0, 8);
      if (titles.length === 0) {
        toast.error('标题生成失败：服务器返回了空内容');
        return [];
      }
      toast.success('标题生成完成');
      return titles;
    } finally {
      finishAction('title');
    }
  }, [
    beginAction,
    finishAction,
    generateTitleMutation,
    selectedModel,
    titleContent,
    titleContentIdentity,
  ]);

  const handleClear = () => {
    setPendingEditAction({ kind: 'clear' });
  };

  const handleSetCurrentVersion = (versionId: string) => {
    if (versionId === currentVersionId) return;
    if (isEdited) {
      setPendingEditAction({ kind: 'switch-version', versionId });
      return;
    }
    setCurrentVersion(versionId);
  };

  const handleSaveEdit = () => {
    const versionId = saveEdit();
    if (versionId) toast.success('编辑内容已保存为新版本');
  };

  const handleDiscardEdit = () => {
    if (isEdited) setPendingEditAction({ kind: 'discard-edit' });
  };

  const confirmPendingEditAction = () => {
    if (!pendingEditAction) return;
    if (pendingEditAction.kind === 'switch-version') {
      discardEdit();
      setCurrentVersion(pendingEditAction.versionId);
    } else if (pendingEditAction.kind === 'clear') {
      clear();
      setCustomInstruction('');
    } else {
      discardEdit();
    }
    setPendingEditAction(null);
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.repeat) return;
      const hasCommandModifier = e.ctrlKey || e.metaKey;
      if (hasCommandModifier && e.key === 'Enter') {
        const active = document.activeElement as HTMLElement;
        if (active?.id === 'postSourceInput') {
          e.preventDefault();
          void handleTranslate();
        }
      }
      if (hasCommandModifier && e.key.toLowerCase() === 'k') {
        const active = document.activeElement as HTMLElement;
        if (active?.id === 'customInstructionInput' || active?.id === 'translationEditor') {
          e.preventDefault();
          const instruction = customInstruction.trim();
          if (instruction) {
            void handleOptimize({ instruction }).then(completed => {
              if (completed) {
                setCustomInstruction(current =>
                  current.trim() === instruction ? '' : current
                );
              }
            });
          } else {
            document.getElementById('customInstructionInput')?.focus();
          }
        }
      }
      if (e.key === 'Escape' && isEdited) {
        e.preventDefault();
        setPendingEditAction({ kind: 'discard-edit' });
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [customInstruction, handleOptimize, handleTranslate, isEdited]);

  useEffect(() => {
    if (!isEdited) return;
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isEdited]);

  return (
    <div className="min-h-full overflow-auto">
      <div className="mx-auto w-full max-w-7xl px-4 py-4 sm:px-6 sm:py-6">
        <div className="mb-5 flex flex-col gap-4 sm:mb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">帖子翻译</h2>
            <p className="text-sm text-muted-foreground">翻译、优化并生成标题</p>
          </div>
          <div className="w-full sm:w-64">
            <label className="block text-xs text-text-muted mb-1.5">选择模型</label>
            <ModelSelector
              value={selectedModel}
              onChange={setSelectedModel}
              className="h-9 text-sm"
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 lg:gap-6">
          <SourceInput
            value={originalText}
            onChange={setOriginalText}
            onTranslate={() => void handleTranslate()}
            onClear={handleClear}
            isLoading={isLoading}
            isTranslating={pendingAction === 'translate'}
            canClear={!!(originalText.trim() || versions.length > 0 || currentContent)}
          />

          <div className="flex min-w-0 flex-col gap-5">
            <TranslationOutput
              versions={versions}
              currentVersionId={currentVersionId}
              currentSourceRevision={sourceRevision}
              currentContent={currentContent}
              isEdited={isEdited}
              editedContent={editedContent}
              onSetCurrentVersion={handleSetCurrentVersion}
              onSetEditedContent={setEditedContent}
              onSaveEdit={handleSaveEdit}
              onDiscardEdit={handleDiscardEdit}
            />

            <OptimizationPanel
              onOptimize={handleOptimize}
              isLoading={isLoading}
              isOptimizing={pendingAction === 'optimize'}
              hasVersions={versions.length > 0}
              hasOriginal={!!(currentVersion?.sourceText.trim() || originalText.trim())}
              customInstruction={customInstruction}
              onCustomInstructionChange={setCustomInstruction}
            />

            <TitleGenerator
              onGenerate={handleGenerateTitle}
              isLoading={isLoading}
              isGenerating={pendingAction === 'title'}
              canGenerate={versions.length > 0 || !!originalText}
              contentIdentity={titleContentIdentity}
            />
          </div>
        </div>
      </div>

      <AlertDialog
        open={pendingEditAction !== null}
        onOpenChange={(open) => {
          if (!open) setPendingEditAction(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pendingEditAction?.kind === 'clear' ? '清空帖子工作区' : '放弃未保存的编辑'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingEditAction?.kind === 'clear'
                ? '原文、译文版本和生成的标题都会被清空，此操作无法撤销。'
                : '当前译文有尚未保存的修改。继续后，这些修改将被放弃。'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>返回编辑</AlertDialogCancel>
            <AlertDialogAction onClick={confirmPendingEditAction}>
              {pendingEditAction?.kind === 'clear' ? '确认清空' : '放弃修改'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
