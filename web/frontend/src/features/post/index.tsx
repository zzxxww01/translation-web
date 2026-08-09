import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { usePostStore } from '@/shared/stores';
import type { PostNetworkAction } from '@/shared/stores/postStore';
import { useTranslatePost, useOptimizePost, useGenerateTitle } from './hooks';
import { TranslationVersionType } from '@/shared/constants';
import { SourceInput } from './components/SourceInput';
import { TranslationOutput } from './components/TranslationOutput';
import { OptimizationPanel } from './components/OptimizationPanel';
import { TitleGenerator } from './components/TitleGenerator';
import { ModelSelector } from '@/components/ModelSelector';
import { Button } from '@/components/ui/Button';
import { Loader2, X } from 'lucide-react';
import { POST_CONTENT_MAX_LENGTH, describeOptimizeOption } from './types';
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

// 只剩「会丢掉未保存编辑」的两种动作需要拦一道。清空按用户要求直接执行。
type PendingEditAction =
  | { kind: 'switch-version'; versionId: string }
  | { kind: 'discard-edit' };

const ACTION_LABELS: Record<PostNetworkAction, string> = {
  translate: '正在翻译',
  optimize: '正在优化译文',
  title: '正在生成标题',
};

// 模块级状态：PostFeature 是懒加载路由组件，切走会被卸载。
// 取消句柄与请求代际放在模块作用域，才能在重新挂载后仍然可用。
let activeAbortController: AbortController | null = null;
// 请求代际：每发起或取消一次请求就 +1。返回结果只有代际匹配时才写入，
// 从而保证「取消」之后到达的结果一定不会落库。
let requestGeneration = 0;

export function PostFeature() {
  const {
    originalText, sourceRevision, versions, currentVersionId, isEdited, editedContent, isLoading,
    pendingAction, pendingStartedAt, selectedModel,
    setOriginalText, addVersion, setCurrentVersion, setEditedContent,
    saveEdit, discardEdit, clear, setPendingAction, setSelectedModel,
  } = usePostStore();

  const translateMutation = useTranslatePost();
  const optimizeMutation = useOptimizePost();
  const generateTitleMutation = useGenerateTitle();
  const [customInstruction, setCustomInstruction] = useState('');
  const [pendingEditAction, setPendingEditAction] = useState<PendingEditAction | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const currentVersion = versions.find(v => v.id === currentVersionId);
  const currentContent = isEdited ? editedContent : currentVersion?.content || '';
  const titleContent = currentContent.trim() ? currentContent : originalText;
  const titleContentIdentity = currentVersionId
    ? `version:${currentVersionId}:${currentContent}`
    : `source:${sourceRevision}:${originalText}`;

  const beginAction = useCallback((action: PostNetworkAction) => {
    // 互斥判断读 store，避免重新挂载的新实例绕过本地 ref 再发起一次并发请求
    if (usePostStore.getState().pendingAction) return null;
    const controller = new AbortController();
    activeAbortController = controller;
    requestGeneration += 1;
    const generation = requestGeneration;
    setPendingAction(action);
    return { controller, generation };
  }, [setPendingAction]);

  const finishAction = useCallback((controller: AbortController) => {
    // 只有仍然是当前请求时才解除加载态（已取消/已被替换的请求不干扰新请求）
    if (activeAbortController !== controller) return;
    activeAbortController = null;
    setPendingAction(null);
  }, [setPendingAction]);

  const cancelActiveAction = useCallback(() => {
    // 代际 +1：即便后端仍在跑，返回结果也不会再写入
    requestGeneration += 1;
    activeAbortController?.abort(
      new DOMException('user-cancel', 'AbortError')
    );
    activeAbortController = null;
    setPendingAction(null);
    toast.info('已取消，本次结果不再写入');
  }, [setPendingAction]);

  const requestVersionSwitch = useCallback((versionId: string) => {
    const state = usePostStore.getState();
    if (versionId === state.currentVersionId) return;
    if (state.isEdited) {
      setPendingEditAction({ kind: 'switch-version', versionId });
      return;
    }
    setCurrentVersion(versionId);
  }, [setCurrentVersion]);

  const preserveCurrentEdit = useCallback(() => {
    if (!usePostStore.getState().isEdited) return null;
    const versionId = saveEdit();
    if (versionId) toast.info('未保存的译文已另存为手工版本');
    return versionId;
  }, [saveEdit]);

  const handleTranslate = useCallback(async (): Promise<boolean> => {
    const sourceText = originalText;
    const requestSourceRevision = sourceRevision;
    if (!sourceText.trim()) return false;
    const request = beginAction('translate');
    if (!request) return false;
    preserveCurrentEdit();
    try {
      const result = await translateMutation.mutateAsync({
        content: sourceText,
        model: selectedModel,
        signal: request.controller.signal,
      });
      // 已被用户取消：结果一律丢弃
      if (request.generation !== requestGeneration) return false;
      if (!result.translation?.trim()) {
        toast.error('翻译失败：服务器返回了空内容');
        return false;
      }

      const latest = usePostStore.getState();
      const isStale =
        latest.sourceRevision !== requestSourceRevision ||
        latest.originalText !== sourceText;

      // 等待期间原文被改过时，结果不再整份丢弃，而是作为旁支版本落库
      const versionId = addVersion(
        result.translation,
        TranslationVersionType.TRANSLATION,
        undefined,
        {
          sourceRevision: requestSourceRevision,
          sourceText,
          makeCurrent: !isStale,
        }
      );
      if (isStale) {
        toast.info('原文已更新，本次译文已另存为旧底稿版本', {
          action: { label: '查看', onClick: () => requestVersionSwitch(versionId) },
        });
        return true;
      }
      toast.success('翻译完成');
      return true;
    } catch (error) {
      console.error('翻译失败:', error);
      return false;
    } finally {
      finishAction(request.controller);
    }
  }, [
    addVersion,
    beginAction,
    finishAction,
    originalText,
    preserveCurrentEdit,
    requestVersionSwitch,
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
    const request = beginAction('optimize');
    if (!request) return false;

    const savedEditVersionId = preserveCurrentEdit();
    const baseVersionId = savedEditVersionId ?? activeVersion.id;
    const stateAfterPreserve = usePostStore.getState();
    const baseVersion = stateAfterPreserve.versions.find(v => v.id === baseVersionId);
    if (!baseVersion) {
      finishAction(request.controller);
      return false;
    }
    const baseSourceText = baseVersion.sourceText.trim()
      ? baseVersion.sourceText
      : stateAfterPreserve.originalText;
    const baseSourceRevision = baseVersion.sourceText.trim()
      ? baseVersion.sourceRevision
      : stateAfterPreserve.sourceRevision;
    if (!baseSourceText.trim()) {
      finishAction(request.controller);
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
        signal: request.controller.signal,
      });
      if (request.generation !== requestGeneration) return false;
      if (!result.optimized_translation?.trim()) {
        toast.error('优化失败：服务器返回了空内容');
        return false;
      }

      const latest = usePostStore.getState();
      const latestBaseVersion = latest.versions.find(v => v.id === baseVersionId);
      const isStale =
        latest.currentVersionId !== baseVersionId ||
        latest.isEdited ||
        latestBaseVersion?.content !== translationAtStart;

      // 版本体系是 append-only，等待期间的编辑/切版本不应该让优化结果作废；
      // makeCurrent:false 保证不会顶掉用户当前未保存的编辑
      const versionId = addVersion(
        result.optimized_translation,
        TranslationVersionType.OPTIMIZATION,
        // 记录人话摘要而不是内部 id：版本下拉与多轮优化历史都会读这个字段
        options.optionId ? describeOptimizeOption(options.optionId) : options.instruction,
        {
          sourceRevision: baseSourceRevision,
          sourceText: baseSourceText,
          parentVersionId: baseVersionId,
          makeCurrent: !isStale,
        }
      );
      if (isStale) {
        toast.info('译文已更新，本次优化结果已另存为新版本', {
          action: { label: '查看', onClick: () => requestVersionSwitch(versionId) },
        });
        return true;
      }
      toast.success('优化完成');
      return true;
    } catch (error) {
      console.error('优化失败:', error);
      return false;
    } finally {
      finishAction(request.controller);
    }
  }, [
    addVersion,
    beginAction,
    currentContent,
    currentVersionId,
    finishAction,
    optimizeMutation,
    preserveCurrentEdit,
    requestVersionSwitch,
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
    const request = beginAction('title');
    if (!request) return [];

    try {
      const result = await generateTitleMutation.mutateAsync({
        content,
        instruction: instruction || undefined,
        model: selectedModel,
        signal: request.controller.signal,
      });
      if (request.generation !== requestGeneration) return [];

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
      finishAction(request.controller);
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
    clear();
    setCustomInstruction('');
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
    discardEdit();
    if (pendingEditAction.kind === 'switch-version') {
      setCurrentVersion(pendingEditAction.versionId);
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
      // Escape 已下放到译文编辑框自身的 onKeyDown（见 TranslationOutput），
      // 挂在 window 上会与 Radix 弹层/下拉的 Escape 关闭抢同一次事件
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [customInstruction, handleOptimize, handleTranslate]);

  useEffect(() => {
    if (!isEdited) return;
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isEdited]);

  // 等待期间展示已耗时，避免只有一个小转圈、用户无法判断是否卡死
  useEffect(() => {
    if (!pendingAction || !pendingStartedAt) {
      setElapsedSeconds(0);
      return;
    }
    const tick = () =>
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - pendingStartedAt) / 1000)));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [pendingAction, pendingStartedAt]);

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

        {pendingAction && (
          <div
            className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/60 bg-white/85 px-4 py-3 text-sm shadow-sm backdrop-blur-sm"
            role="status"
            aria-live="polite"
          >
            <div className="flex min-w-0 items-center gap-2">
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
              <span className="min-w-0">
                {ACTION_LABELS[pendingAction]}，已用时 {elapsedSeconds} 秒（最长约 3 分钟）
              </span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9"
              onClick={cancelActiveAction}
            >
              <X className="h-4 w-4" /> 取消
            </Button>
          </div>
        )}

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
              originalText={originalText}
              currentContent={currentContent}
              isEdited={isEdited}
              editedContent={editedContent}
              onSetCurrentVersion={requestVersionSwitch}
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
            <AlertDialogTitle>放弃未保存的编辑</AlertDialogTitle>
            <AlertDialogDescription>
              当前译文有尚未保存的修改。继续后，这些修改将被放弃。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>返回编辑</AlertDialogCancel>
            <AlertDialogAction onClick={confirmPendingEditAction}>
              放弃修改
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
