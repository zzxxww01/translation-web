import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle } from 'lucide-react';
import { toast } from 'sonner';
import { ModelSelector } from '@/components/ModelSelector';
import { ResizablePanes } from '@/components/layout/ResizablePanes';
import { Button } from '@/components/ui/Button';
import { usePostStore } from '@/shared/stores';
import { SourceInput } from './components/SourceInput';
import { TranslationOutput } from './components/TranslationOutput';
import { OptimizationPanel } from './components/OptimizationPanel';
import { TitleGenerator } from './components/TitleGenerator';
import { DraftHistory } from './components/DraftHistory';
import { DiscardEditDialog, PendingChip, SaveState } from './components/WorkspaceChrome';
import { draftsApi, useDraftSync, type DraftSummary } from './drafts';
import { usePostWorkspace } from './usePostWorkspace';

/**
 * 帖子翻译页：粘贴原文 → 翻译 → 优化 → 标题（老用法不变）。左边多了「翻译记录」栏：
 * 这里手动翻的和 Slack 里翻的都在，内容自动存到服务器。三栏都能收起、能拖宽。
 */
export function PostFeature() {
  const ws = usePostWorkspace(usePostStore);
  const draftId = usePostStore(state => state.draftId);
  const navigate = useNavigate();
  const [status, setStatus] = useState<'draft' | 'done'>('draft');
  const sync = useDraftSync(usePostStore, { extra: () => ({ status }) });

  const openDraft = async (item: DraftSummary) => {
    if (item.source === 'slack' && item.slack) {
      navigate(`/slack?mode=translate&tc=${item.slack.channel_id}&t=${item.slack.thread_ts}`);
      return;
    }
    await sync.flush();
    const doc = await draftsApi.get(item.id);
    usePostStore.getState().loadSnapshot(doc.state, doc.id, doc.rev);
    setStatus(doc.status);
    sync.markLoaded();
  };

  const newDraft = async () => {
    await sync.flush();
    ws.handleClear();
    setStatus('draft');
  };

  const toggleDone = () => {
    const next = status === 'done' ? 'draft' : 'done';
    setStatus(next);
    // status 不在 store 里：下一轮自动存档会带上
    window.setTimeout(() => void sync.flush(), 0);
    toast.success(next === 'done' ? '已标记完成' : '已改回草稿');
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border-subtle bg-white/60 px-5 py-2.5">
        <h1 className="text-lg font-semibold text-text-primary" style={{ fontFamily: 'var(--font-display)' }}>帖子翻译</h1>
        <SaveState saving={sync.saving} savedAt={sync.savedAt} hasDraft={!!draftId} />
        <div className="ml-auto flex items-center gap-2">
          <PendingChip ws={ws} />
          {draftId && (
            <Button variant={status === 'done' ? 'secondary' : 'outline'} size="sm" className="h-9" onClick={toggleDone}>
              {status === 'done' ? <CheckCircle2 className="h-4 w-4 text-success" /> : <Circle className="h-4 w-4" />}
              {status === 'done' ? '已完成' : '标记完成'}
            </Button>
          )}
          <div className="w-52" title="翻译用的模型">
            <ModelSelector value={ws.selectedModel} onChange={ws.setSelectedModel} className="h-9 text-sm" disabled={ws.isLoading} />
          </div>
        </div>
      </div>

      <ResizablePanes
        storageKey="post-panes-v1"
        mobileDefault="source"
        panes={[
          {
            id: 'history',
            title: '翻译记录',
            width: 300,
            minWidth: 240,
            content: <DraftHistory activeId={draftId} onOpen={item => void openDraft(item)} onNew={() => void newDraft()} />,
          },
          {
            id: 'source',
            title: '原文',
            width: 460,
            minWidth: 300,
            content: (
              <div className="flex h-full flex-col p-4">
                <SourceInput
                  hideTitle
                  value={ws.originalText}
                  onChange={ws.setOriginalText}
                  onTranslate={() => void ws.handleTranslate()}
                  onClear={() => void newDraft()}
                  isLoading={ws.isLoading}
                  isTranslating={ws.pendingAction === 'translate'}
                  canClear={!!(ws.originalText.trim() || ws.versions.length > 0 || ws.currentContent)}
                  className="min-h-[320px] flex-1 resize-none"
                />
              </div>
            ),
          },
          {
            id: 'work',
            title: '译文 · 优化 · 标题',
            minWidth: 380,
            content: <WorkColumn ws={ws} />,
          },
        ]}
      />
      <DiscardEditDialog ws={ws} />
    </div>
  );
}

/** 译文、优化指令、标题三块：帖子翻译页和 Slack 翻译模式共用 */
export function WorkColumn({ ws, extraActions }: { ws: ReturnType<typeof usePostWorkspace>; extraActions?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-5 p-4">
      <TranslationOutput
        hideTitle
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
