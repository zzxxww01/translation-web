import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import type { PostNetworkAction, PostStoreHook } from '@/shared/stores/postStore';
import { TranslationVersionType } from '@/shared/constants';
import { useGenerateTitle, useOptimizePost, useTranslatePost } from './hooks';
import { POST_CONTENT_MAX_LENGTH, describeOptimizeOption } from './types';
import { getOptimizationHistory } from './versionLineage';

// 只剩「会丢掉未保存编辑」的两种动作需要拦一道。清空按用户要求直接执行。
export type PendingEditAction =
  | { kind: 'switch-version'; versionId: string }
  | { kind: 'discard-edit' };

export const ACTION_LABELS: Record<PostNetworkAction, string> = {
  translate: '正在翻译',
  optimize: '正在优化译文',
  title: '正在生成标题',
  hashtags: '正在生成标签',
};

// 取消句柄与请求代际按 store 放在模块作用域：工作区组件切走会被卸载，重新挂载后仍要能取消、能丢弃过期结果。
// 请求代际：每发起或取消一次请求就 +1。返回结果只有代际匹配时才写入，保证「取消」之后到达的结果不会落库。
const requests = new WeakMap<PostStoreHook, { controller: AbortController | null; generation: number }>();
function requestState(store: PostStoreHook) {
  let entry = requests.get(store);
  if (!entry) {
    entry = { controller: null, generation: 0 };
    requests.set(store, entry);
  }
  return entry;
}

/**
 * 帖子翻译工作区的全部交互：翻译、优化、标题、版本切换和编辑。帖子翻译页和 Slack 翻译模式共用，
 * 区别只在传进来的 store（帖子翻译页一份持久化的，Slack 每篇帖子一份）和外面的布局。
 */
export function usePostWorkspace(useStore: PostStoreHook, { shortcuts = true }: { shortcuts?: boolean } = {}) {
  const {
    originalText, sourceRevision, versions, currentVersionId, isEdited, editedContent, isLoading,
    pendingAction, pendingStartedAt, selectedModel,
    setOriginalText, addVersion, setCurrentVersion, setEditedContent,
    saveEdit, discardEdit, clear, setPendingAction, setSelectedModel,
    generatedTitles, selectedTitle, titleContentIdentity: savedTitleContentIdentity,
    setGeneratedTitles, setSelectedTitle,
  } = useStore();

  const translateMutation = useTranslatePost();
  const optimizeMutation = useOptimizePost();
  const generateTitleMutation = useGenerateTitle();
  const [customInstruction, setCustomInstruction] = useState('');
  const [pendingEditAction, setPendingEditAction] = useState<PendingEditAction | null>(null);
  const [clock, setClock] = useState({ startedAt: 0, elapsed: 0 });
  const elapsedSeconds = pendingAction && pendingStartedAt === clock.startedAt ? clock.elapsed : 0;
  /** 每次「清空」自增，用作 TitleGenerator 的 key，重置它内部的输入框 */
  const [clearToken, setClearToken] = useState(0);

  const currentVersion = versions.find(v => v.id === currentVersionId);
  const currentContent = isEdited ? editedContent : currentVersion?.content || '';
  const titleContent = currentContent.trim() ? currentContent : originalText;
  const titleContentIdentity = currentVersionId
    ? `version:${currentVersionId}:${currentContent}`
    : `source:${sourceRevision}:${originalText}`;

  const beginAction = ((action: PostNetworkAction) => {
    // 互斥判断读 store，避免重新挂载的新实例绕过本地 ref 再发起一次并发请求
    if (useStore.getState().pendingAction) return null;
    const entry = requestState(useStore);
    const controller = new AbortController();
    entry.controller = controller;
    entry.generation += 1;
    const generation = entry.generation;
    setPendingAction(action);
    return { controller, generation };
  });

  const isCurrentRequest = (generation: number) => requestState(useStore).generation === generation;

  const finishAction = ((controller: AbortController) => {
    // 只有仍然是当前请求时才解除加载态（已取消/已被替换的请求不干扰新请求）
    const entry = requestState(useStore);
    if (entry.controller !== controller) return;
    entry.controller = null;
    setPendingAction(null);
  });

  const cancelActiveAction = (() => {
    // 代际 +1：即便后端仍在跑，返回结果也不会再写入
    const entry = requestState(useStore);
    entry.generation += 1;
    entry.controller?.abort(new DOMException('user-cancel', 'AbortError'));
    entry.controller = null;
    setPendingAction(null);
    toast.info('已取消，本次结果不再写入');
  });

  const requestVersionSwitch = ((versionId: string) => {
    const state = useStore.getState();
    if (versionId === state.currentVersionId) return;
    if (state.isEdited) {
      setPendingEditAction({ kind: 'switch-version', versionId });
      return;
    }
    setCurrentVersion(versionId);
  });

  const preserveCurrentEdit = () => {
    if (!useStore.getState().isEdited) return null;
    const versionId = saveEdit();
    if (versionId) toast.info('未保存的译文已另存为手工版本');
    return versionId;
  };

  const handleTranslate = (async (): Promise<boolean> => {
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
      if (!isCurrentRequest(request.generation)) return false;
      if (!result.translation?.trim()) {
        toast.error('翻译失败：服务器返回了空内容');
        return false;
      }

      const latest = useStore.getState();
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
          modelAlias: selectedModel,
          modelUsed: result.model_used,
          providerUsed: result.provider_used,
          fallbackUsed: result.fallback_used,
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
  });

  const handleOptimize = async (
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
    const stateAfterPreserve = useStore.getState();
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

    const history = getOptimizationHistory(stateAfterPreserve.versions, baseVersionId, 3);

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
      if (!isCurrentRequest(request.generation)) return false;
      if (!result.optimized_translation?.trim()) {
        toast.error('优化失败：服务器返回了空内容');
        return false;
      }

      const latest = useStore.getState();
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
          modelAlias: selectedModel,
          modelUsed: result.model_used,
          providerUsed: result.provider_used,
          fallbackUsed: result.fallback_used,
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
  };

  const handleGenerateTitle = (async (instruction?: string): Promise<string[]> => {
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
      if (!isCurrentRequest(request.generation)) return [];

      const latest = useStore.getState();
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
      setGeneratedTitles(titles, contentIdentity);
      toast.success('标题生成完成');
      return titles;
    } finally {
      finishAction(request.controller);
    }
  });

  const handleClear = () => {
    clear();
    setCustomInstruction('');
    // TitleGenerator 的「标题要求」输入框是组件内部 state，store 的 clear()
    // 够不着它。换 key 强制重挂载，把它一并清干净。
    setClearToken(token => token + 1);
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

  const shortcutHandlers = useRef({ handleOptimize, handleTranslate, customInstruction });
  useLayoutEffect(() => { shortcutHandlers.current = { handleOptimize, handleTranslate, customInstruction }; });

  useEffect(() => {
    if (!shortcuts) return;
    const handler = (e: KeyboardEvent) => {
      if (e.repeat) return;
      const { handleTranslate, handleOptimize, customInstruction } = shortcutHandlers.current;
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
                setCustomInstruction(current => (current.trim() === instruction ? '' : current));
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
  }, [shortcuts]);

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
    if (!pendingAction || !pendingStartedAt) return;
    const tick = () =>
      setClock({ startedAt: pendingStartedAt, elapsed: Math.max(0, Math.floor((Date.now() - pendingStartedAt) / 1000)) });
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [pendingAction, pendingStartedAt]);

  return {
    originalText, setOriginalText, versions, currentVersionId, currentVersion, currentContent,
    isEdited, editedContent, setEditedContent, isLoading, pendingAction, elapsedSeconds,
    selectedModel, setSelectedModel, generatedTitles, selectedTitle, setSelectedTitle,
    savedTitleContentIdentity, titleContentIdentity, customInstruction, setCustomInstruction,
    clearToken, pendingEditAction, setPendingEditAction,
    cancelActiveAction, requestVersionSwitch, handleTranslate, handleOptimize, handleGenerateTitle,
    handleClear, handleSaveEdit, handleDiscardEdit, confirmPendingEditAction,
  };
}

export type PostWorkspace = ReturnType<typeof usePostWorkspace>;
