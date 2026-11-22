import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { History } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { ModelSelector } from '@/components/ModelSelector';
import { Button } from '@/components/ui/Button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { usePostStore } from '@/shared/stores';
import { SourceInput } from './components/SourceInput';
import { TranslationOutput } from './components/TranslationOutput';
import { OptimizationPanel } from './components/OptimizationPanel';
import { TitleGenerator } from './components/TitleGenerator';
import { DraftHistory } from './components/DraftHistory';
import { DiscardEditDialog, PendingChip } from './components/WorkspaceChrome';
import { draftsApi, useDraftSync, type DraftSummary } from './drafts';
import { usePostWorkspace } from './usePostWorkspace';

/**
 * 帖子翻译页（旧功能，以后逐步迁到 Slack 里）：布局和用法保持原样——粘贴原文 → 翻译 → 优化 → 标题。
 * 2026-11-22 只加了一样：右上角「历史记录」，点开才展开（Slack 里翻的和这里翻的都在）。
 * 这里出过译文的内容会自动存进历史记录。
 */
export function PostFeature() {
  const ws = usePostWorkspace(usePostStore);
  const draftId = usePostStore(state => state.draftId);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [historyOpen, setHistoryOpen] = useState(false);
  const sync = useDraftSync(usePostStore);

  const openDraft = async (item: Pick<DraftSummary, 'id' | 'source' | 'slack'>) => {
    if (item.source === 'slack' && item.slack) {
      navigate(`/slack?mode=translate&tc=${item.slack.channel_id}&t=${item.slack.thread_ts}`);
      return;
    }
    await sync.flush();
    const doc = await draftsApi.get(item.id);
    usePostStore.getState().loadSnapshot(doc.state, doc.id, doc.rev);
    sync.markLoaded();
    setHistoryOpen(false);
  };

  // 从 Slack 的「全部翻译记录」点过来：/post?draft=<id>
  const opened = useRef<string | null>(null);
  const linked = params.get('draft');
  useEffect(() => {
    if (!linked || opened.current === linked) return;
    opened.current = linked;
    const timer = window.setTimeout(() => {
      void openDraft({ id: linked, source: 'manual', slack: null });
      setParams({}, { replace: true });
    }, 0);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linked]);

  const newDraft = async () => {
    await sync.flush();
    ws.handleClear();
    setHistoryOpen(false);
  };

  return (
    <div className="min-h-full overflow-auto">
      <div className="mx-auto w-full max-w-7xl px-4 pb-12 pt-4 sm:px-8 sm:pt-5">
        <PageHeader
          className="mb-5"
          title="帖子翻译"
          actions={
            <>
              <PendingChip ws={ws} />
              <div className="hidden w-48 sm:block lg:w-40 xl:w-48" title="翻译用的模型">
                <ModelSelector value={ws.selectedModel} onChange={ws.setSelectedModel} className="h-9 text-sm" disabled={ws.isLoading} />
              </div>
              <Button variant="ghost" size="sm" className="h-9" onClick={() => setHistoryOpen(true)} title="Slack 里翻的和这里翻的都在">
                <History className="h-4 w-4" /> <span className="hidden sm:inline lg:hidden xl:inline">历史记录</span>
              </Button>
            </>
          }
        />

        {/* 手机顶栏放不下模型选择，挪到正文最上面 */}
        <div className="mb-3 sm:hidden">
          <ModelSelector value={ws.selectedModel} onChange={ws.setSelectedModel} className="h-9 text-sm" disabled={ws.isLoading} />
        </div>
        {/* 上面原文 / 译文两张等高的纸，下面一排优化和标题；手机上依次往下排 */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-5">
          <SourceInput
            value={ws.originalText}
            onChange={ws.setOriginalText}
            onTranslate={() => void ws.handleTranslate()}
            onClear={() => void newDraft()}
            isLoading={ws.isLoading}
            isTranslating={ws.pendingAction === 'translate'}
            canClear={!!(ws.originalText.trim() || ws.versions.length > 0 || ws.currentContent)}
          />
          <WorkColumn ws={ws} showTitle layout="page" />
        </div>
      </div>

      <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
        <SheetContent side="right" className="flex w-[380px] flex-col p-0 sm:max-w-[380px]">
          <SheetHeader className="border-b border-border-subtle px-4 py-3">
            <SheetTitle className="text-base">历史记录</SheetTitle>
          </SheetHeader>
          <div className="min-h-0 flex-1">
            <DraftHistory activeId={draftId} onOpen={item => void openDraft(item)} onNew={() => void newDraft()} />
          </div>
        </SheetContent>
      </Sheet>
      <DiscardEditDialog ws={ws} />
    </div>
  );
}

/** 译文、优化指令、标题三块：帖子翻译页和 Slack 翻译模式共用 */
export function WorkColumn({ ws, extraActions, showTitle = false, layout = 'column' }: {
  ws: ReturnType<typeof usePostWorkspace>;
  extraActions?: React.ReactNode;
  /** 帖子翻译页保留原来的「译文」小标题；Slack 分栏里栏头已经写了 */
  showTitle?: boolean;
  /** page：帖子翻译页，译文和原文并排、优化和标题排到下一行；column：Slack 分栏里一列排下来 */
  layout?: 'page' | 'column';
}) {
  return (
    <div className={layout === 'page' ? 'contents' : 'flex flex-col gap-5 p-4'}>
      <TranslationOutput
        hideTitle={!showTitle}
        versions={ws.versions}
        currentVersionId={ws.currentVersionId}
        originalText={ws.originalText}
        currentContent={ws.currentContent}
        isEdited={ws.isEdited}
        editedContent={ws.editedContent}
        onSetCurrentVersion={ws.requestVersionSwitch}
        onSetEditedContent={ws.setEditedContent}
        onSaveEdit={ws.handleSaveEdit}
        onDiscardEdit={ws.handleDiscardEdit}
        extraActions={extraActions}
      />
      <OptimizationPanel
        onOptimize={ws.handleOptimize}
        isLoading={ws.isLoading}
        isOptimizing={ws.pendingAction === 'optimize'}
        hasVersions={ws.versions.length > 0}
        hasOriginal={!!(ws.currentVersion?.sourceText.trim() || ws.originalText.trim())}
        customInstruction={ws.customInstruction}
        onCustomInstructionChange={ws.setCustomInstruction}
      />
      <TitleGenerator
        key={ws.clearToken}
        onGenerate={ws.handleGenerateTitle}
        isLoading={ws.isLoading}
        isGenerating={ws.pendingAction === 'title'}
        canGenerate={ws.versions.length > 0 || !!ws.originalText}
        contentIdentity={ws.titleContentIdentity}
        titles={ws.generatedTitles}
        titlesContentIdentity={ws.savedTitleContentIdentity}
        selectedTitle={ws.selectedTitle}
        onSelectTitle={ws.setSelectedTitle}
      />
    </div>
  );
}
