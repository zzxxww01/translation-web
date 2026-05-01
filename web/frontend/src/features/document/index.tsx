import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import type { TermReviewDecision } from '../confirmation/types';
import { useDocumentStore } from '@/shared/stores';
import { TranslationMethod } from '@/shared/constants';
import type { Paragraph, Section } from '@/shared/types';
import { documentApi } from './api';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/Button';
import { PanelLeftOpen } from 'lucide-react';
import { DocumentSidebar } from './components/DocumentSidebar';
import { EditPanel } from './components/EditPanel';
import { NewProjectModal } from './components/NewProjectModal';
import { SectionView } from './components/SectionView';
import { WelcomeScreen } from './components/WelcomeScreen';
import {
  useDocumentViewState,
  useFullTranslate,
  useProject,
  useSection,
  useTermConflictDialog,
  useTermReviewFlow,
  useTranslationStatusSync,
} from './hooks';

const GlossaryCenter = lazy(() =>
  import('../glossary/GlossaryCenter').then(module => ({ default: module.GlossaryCenter }))
);
const ImmersiveEditor = lazy(() =>
  import('./components/ImmersiveEditor').then(module => ({ default: module.ImmersiveEditor }))
);
const TerminologyReviewPage = lazy(() =>
  import('./components/TerminologyReviewPage').then(module => ({
    default: module.TerminologyReviewPage,
  }))
);

function LazyPanelFallback() {
  return (
    <div className="flex min-h-[220px] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
    </div>
  );
}

export function DocumentFeature() {
  const {
    currentProject,
    setCurrentProject,
    currentSection,
    setCurrentSection,
    currentParagraph,
    sections,
    setSections,
    setCurrentParagraph,
  } = useDocumentStore();

  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [immersiveTargetParagraphId, setImmersiveTargetParagraphId] = useState<string | null>(null);

  // AlertDialog 状态
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [showStartDialog, setShowStartDialog] = useState(false);
  const [pendingStartMethod, setPendingStartMethod] = useState<TranslationMethod>(TranslationMethod.FOUR_STEP);
  const [pendingStartModel, setPendingStartModel] = useState<string | undefined>(undefined);

  const isFullTranslating = useDocumentStore(state => state.isFullTranslating);
  const fullTranslateProgress = useDocumentStore(state => state.fullTranslateProgress);

  useProject(currentProject?.id ?? '');
  const {
    activeSectionId,
    activeView,
    isImmersiveMode,
    setView,
    updateRouteParams,
  } = useDocumentViewState({
    currentSectionId: currentSection?.section_id,
    sections,
    selectedSectionId,
  });
  const {
    backendTranslationStatus,
    currentStep,
    setBackendTranslationStatus,
    setCurrentStep,
  } = useTranslationStatusSync(currentProject?.id);
  const {
    closeWithDefaultResolution,
    conflictDialogOpen,
    currentConflict,
    resolveConflict,
  } = useTermConflictDialog();

  const {
    isLoading: sectionLoading,
    data: sectionData,
    refetch: refetchSection,
  } = useSection(currentProject?.id ?? '', activeSectionId ?? '');

  const { startTranslation, stopTranslation } = useFullTranslate();

  const runFullTranslate = useCallback(
    async (method: TranslationMethod = TranslationMethod.FOUR_STEP, model?: string) => {
      if (!currentProject) return;

      const methodType = method === TranslationMethod.FOUR_STEP ? 'four-step' : 'normal';
      await startTranslation(
        currentProject.id,
        data => {
          if (data.step || data.message) {
            setCurrentStep(data.step || data.message || null);
          }
        },
        () => {
          setCurrentStep(null);
          setBackendTranslationStatus(null);
          if (activeSectionId) {
            refetchSection();
          }
        },
        methodType,
        model
      );
    },
    [activeSectionId, currentProject, refetchSection, setBackendTranslationStatus, setCurrentStep, startTranslation]
  );

  const {
    cancelTermReview,
    isPreparingFullTranslate,
    isSubmittingTermReview,
    pendingTermReview,
    prepareTermReviewIfNeeded,
    setIsPreparingFullTranslate,
    submitTermReview,
  } = useTermReviewFlow({
    currentProjectId: currentProject?.id,
    setView,
    runFullTranslate,
  });

  useEffect(() => {
    if (activeView === 'term-review' && !pendingTermReview) {
      setView(null);
    }
  }, [activeView, pendingTermReview, setView]);

  const selectedSection = useMemo(() => {
    if (!activeSectionId) {
      return null;
    }
    return (
      sections.find(section => section.section_id === activeSectionId) ??
      (currentSection?.section_id === activeSectionId ? currentSection : null)
    );
  }, [activeSectionId, currentSection, sections]);

  const displaySection = useMemo(
    () => sectionData || selectedSection,
    [sectionData, selectedSection]
  );

  const setImmersiveMode = useCallback(
    (enabled: boolean) => {
      updateRouteParams({ immersive: enabled });
    },
    [updateRouteParams]
  );

  const handleSelectSection = useCallback(
    (section: Section) => {
      setSelectedSectionId(section.section_id);
      setCurrentSection(section);
      setCurrentParagraph(null);
      if (activeView) {
        updateRouteParams({ view: null, immersive: false });
      } else {
        updateRouteParams({ immersive: false });
      }
    },
    [activeView, setCurrentParagraph, setCurrentSection, updateRouteParams]
  );

  const handleSelectSectionById = useCallback(
    (sectionId: string) => {
      const section = sections.find(item => item.section_id === sectionId);
      if (section) {
        handleSelectSection(section);
      }
    },
    [handleSelectSection, sections]
  );

  const handleMobileSelectSectionById = useCallback(
    (sectionId: string) => {
      handleSelectSectionById(sectionId);
      setIsMobileSidebarOpen(false);
    },
    [handleSelectSectionById]
  );

  const handleMobileNewProject = useCallback(() => {
    setIsMobileSidebarOpen(false);
    setIsNewProjectModalOpen(true);
  }, []);

  const handleSelectParagraph = useCallback(
    (paragraph: Paragraph) => {
      setCurrentParagraph(paragraph);
    },
    [setCurrentParagraph]
  );

  const handleEnterImmersive = useCallback(() => {
    if (displaySection) {
      setSelectedSectionId(displaySection.section_id);
      setCurrentSection(displaySection);
    }
    setImmersiveTargetParagraphId(currentParagraph?.id ?? null);
    setCurrentParagraph(null);
    setImmersiveMode(true);
  }, [currentParagraph, displaySection, setCurrentParagraph, setCurrentSection, setImmersiveMode]);

  const handleExitImmersive = useCallback(() => {
    setImmersiveTargetParagraphId(null);
    setImmersiveMode(false);
  }, [setImmersiveMode]);

  const getCurrentParagraphIndex = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return -1;
    return displaySection.paragraphs.findIndex(paragraph => paragraph.id === currentParagraph.id);
  }, [displaySection, currentParagraph]);

  const handleNextParagraph = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return;

    const currentIndex = getCurrentParagraphIndex();
    if (currentIndex < displaySection.paragraphs.length - 1) {
      setCurrentParagraph(displaySection.paragraphs[currentIndex + 1]);
      return;
    }

    setCurrentParagraph(null);
  }, [currentParagraph, displaySection, getCurrentParagraphIndex, setCurrentParagraph]);

  const handlePrevParagraph = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return;

    const currentIndex = getCurrentParagraphIndex();
    if (currentIndex > 0) {
      setCurrentParagraph(displaySection.paragraphs[currentIndex - 1]);
    }
  }, [currentParagraph, displaySection, getCurrentParagraphIndex, setCurrentParagraph]);

  const handleFullTranslate = useCallback(
    async (method?: TranslationMethod, model?: string) => {
      if (!currentProject) return;

      if (isPreparingFullTranslate) {
        toast.info('术语预检进行中，请稍候');
        return;
      }

      if (isFullTranslating) {
        setShowStopDialog(true);
        return;
      }

      const selectedMethod = method ?? TranslationMethod.FOUR_STEP;
      setPendingStartMethod(selectedMethod);
      setPendingStartModel(model);
      setShowStartDialog(true);
    },
    [
      currentProject,
      isFullTranslating,
      isPreparingFullTranslate,
    ]
  );

  const handleSubmitTermReview = useCallback(
    async (decisions: TermReviewDecision[]) => {
      await submitTermReview(decisions);
    },
    [submitTermReview]
  );

  const handleCancelTermReview = useCallback(() => {
    cancelTermReview();
  }, [cancelTermReview]);

  const handleProjectCreated = useCallback(
    async (projectId: string) => {
      try {
        const projectData = await documentApi.getProject(projectId);
        setCurrentProject(projectData);
        setSections(projectData.sections ?? []);
        setView(null);
      } catch (error) {
        console.error('Failed to load project:', error);
      }
    },
    [setCurrentProject, setSections, setView]
  );

  const renderMainContent = () => {
    if (!currentProject) {
      return (
        <WelcomeScreen
          onNewProject={() => setIsNewProjectModalOpen(true)}
          onOpenProjects={() => setIsMobileSidebarOpen(true)}
        />
      );
    }

    if (activeView === 'glossary') {
      return (
        <Suspense fallback={<LazyPanelFallback />}>
          <GlossaryCenter
            projectId={currentProject.id}
            projectTitle={currentProject.title}
            defaultScope="project"
            onBack={() => setView(null)}
          />
        </Suspense>
      );
    }

    if (activeView === 'term-review' && pendingTermReview) {
      return (
        <Suspense fallback={<LazyPanelFallback />}>
          <TerminologyReviewPage
            review={pendingTermReview}
            isSubmitting={isSubmittingTermReview}
            onSubmit={handleSubmitTermReview}
            onCancel={handleCancelTermReview}
          />
        </Suspense>
      );
    }

    if (!activeSectionId) {
      return (
        <div className="mx-auto max-w-3xl py-8">
          <div className="mb-6">
            <h2 className="text-xl font-bold">{currentProject.title}</h2>
            <p className="text-text-muted">请选择一个章节开始翻译</p>
          </div>
        </div>
      );
    }

    if (!displaySection && sectionLoading) {
      return (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
        </div>
      );
    }

    if (!displaySection) {
      return (
        <div className="mx-auto max-w-3xl py-8">
          <div className="mb-6">
            <h2 className="text-xl font-bold">{currentProject.title}</h2>
            <p className="text-text-muted">请选择一个章节开始翻译</p>
          </div>
        </div>
      );
    }

    return (
      <SectionView
        key={activeSectionId}
        sections={sections}
        currentSection={displaySection}
        currentParagraph={currentParagraph ?? null}
        isLoading={false}
        isRefetching={sectionLoading}
        onSectionChange={handleSelectSection}
        onParagraphSelect={handleSelectParagraph}
        onEnterImmersive={handleEnterImmersive}
      />
    );
  };

  const currentIndex = getCurrentParagraphIndex();
  const totalCount = displaySection?.paragraphs?.length ?? 0;
  const showEditingPanels = !activeView;
  const hasBackendStatusForCurrentProject =
    backendTranslationStatus?.active_project_id === currentProject?.id;
  const effectiveProgress = hasBackendStatusForCurrentProject
    ? {
        current: backendTranslationStatus?.translated_paragraphs || 0,
        total: backendTranslationStatus?.total_paragraphs || 0,
      }
    : fullTranslateProgress;
  const effectiveIsCancelling = Boolean(
    hasBackendStatusForCurrentProject &&
      backendTranslationStatus?.is_cancelling
  );
  const effectiveIsFullTranslating = Boolean(
    (hasBackendStatusForCurrentProject &&
      backendTranslationStatus?.status === 'processing') ||
      isFullTranslating
  );
  const effectiveCurrentStep =
    (hasBackendStatusForCurrentProject &&
      backendTranslationStatus?.current_step) ||
    currentStep;

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] min-h-0 overflow-hidden md:h-[calc(100dvh-5.5rem)]">
      <DocumentSidebar
        className="hidden md:flex"
        sections={sections}
        activeSectionId={activeSectionId}
        onSectionSelect={handleSelectSectionById}
        onNewProject={() => setIsNewProjectModalOpen(true)}
        onFullTranslate={handleFullTranslate}
        onStopTranslate={() => setShowStopDialog(true)}
        isFullTranslating={effectiveIsFullTranslating}
        isCancelling={effectiveIsCancelling}
        isPreparingFullTranslate={isPreparingFullTranslate}
        fullTranslateProgress={effectiveProgress}
        currentStep={effectiveCurrentStep}
        activeTranslationProjectId={backendTranslationStatus?.active_project_id || null}
        projectId={currentProject?.id}
      />

      <Sheet open={isMobileSidebarOpen} onOpenChange={setIsMobileSidebarOpen}>
        <SheetContent side="left" className="flex w-[88vw] max-w-80 flex-col p-0">
          <SheetHeader className="border-b border-border-subtle px-4 py-4 text-left">
            <SheetTitle className="text-base">项目与章节</SheetTitle>
          </SheetHeader>
          <DocumentSidebar
            className="h-auto min-h-0 w-full flex-1 border-r-0"
            sections={sections}
            activeSectionId={activeSectionId}
            onSectionSelect={handleMobileSelectSectionById}
            onNewProject={handleMobileNewProject}
            onFullTranslate={handleFullTranslate}
            onStopTranslate={() => setShowStopDialog(true)}
            isFullTranslating={effectiveIsFullTranslating}
            isCancelling={effectiveIsCancelling}
            isPreparingFullTranslate={isPreparingFullTranslate}
            fullTranslateProgress={effectiveProgress}
            currentStep={effectiveCurrentStep}
            activeTranslationProjectId={backendTranslationStatus?.active_project_id || null}
            projectId={currentProject?.id}
          />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-border-subtle bg-white/90 px-3 py-2 md:hidden">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsMobileSidebarOpen(true)}
            className="h-10"
          >
            <PanelLeftOpen className="h-4 w-4" />
            章节
          </Button>
          <div className="min-w-0 flex-1 px-3 text-right">
            <div className="truncate text-sm font-semibold text-text-primary">
              {currentProject?.title || '长文翻译'}
            </div>
            {displaySection ? (
              <div className="truncate text-xs text-text-muted">{displaySection.title}</div>
            ) : null}
          </div>
        </div>

        <main className="min-h-0 flex-1 overflow-y-auto">{renderMainContent()}</main>
      </div>

      {showEditingPanels && currentParagraph && currentProject && activeSectionId && displaySection && (
        <EditPanel
          paragraph={currentParagraph}
          projectId={currentProject.id}
          sectionId={activeSectionId}
          onClose={() => setCurrentParagraph(null)}
          onNext={handleNextParagraph}
          onPrev={handlePrevParagraph}
          currentIndex={currentIndex}
          totalCount={totalCount}
          onEnterImmersive={handleEnterImmersive}
        />
      )}

      {showEditingPanels && isImmersiveMode && currentProject && displaySection && (
        <Suspense fallback={<LazyPanelFallback />}>
          <ImmersiveEditor
            projectId={currentProject.id}
            section={displaySection}
            initialParagraphId={immersiveTargetParagraphId}
            onClose={handleExitImmersive}
          />
        </Suspense>
      )}

      <NewProjectModal
        isOpen={isNewProjectModalOpen}
        onClose={() => setIsNewProjectModalOpen(false)}
        onProjectCreated={handleProjectCreated}
      />

      {/* 术语冲突对话框 */}
      <Dialog open={conflictDialogOpen} onOpenChange={(open) => {
        if (!open) {
          closeWithDefaultResolution();
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>术语冲突</DialogTitle>
          </DialogHeader>
          {currentConflict && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                术语 <strong>&ldquo;{currentConflict.term}&rdquo;</strong> 存在不同翻译：
              </p>
              <div className="space-y-2">
                <button
                  className="w-full text-left p-3 border rounded-lg hover:bg-accent transition-colors"
                  onClick={() => {
                    resolveConflict(currentConflict.existing_translation, true);
                  }}
                >
                  <div className="font-medium">保留现有：{currentConflict.existing_translation}</div>
                  {currentConflict.existing_note && (
                    <div className="text-xs text-muted-foreground mt-1">
                      词义说明：{currentConflict.existing_note}
                    </div>
                  )}
                  {currentConflict.existing_context && (
                    <div className="text-xs text-muted-foreground mt-1">
                      上下文：{currentConflict.existing_context}
                    </div>
                  )}
                </button>
                <button
                  className="w-full text-left p-3 border rounded-lg hover:bg-accent transition-colors"
                  onClick={() => {
                    resolveConflict(currentConflict.new_translation, true);
                  }}
                >
                  <div className="font-medium">使用新翻译：{currentConflict.new_translation}</div>
                  {currentConflict.new_note && (
                    <div className="text-xs text-muted-foreground mt-1">
                      词义说明：{currentConflict.new_note}
                    </div>
                  )}
                  {currentConflict.new_context && (
                    <div className="text-xs text-muted-foreground mt-1">
                      上下文：{currentConflict.new_context}
                    </div>
                  )}
                </button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 停止翻译确认对话框 */}
      <AlertDialog open={showStopDialog} onOpenChange={setShowStopDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>停止翻译</AlertDialogTitle>
            <AlertDialogDescription>翻译正在进行中，确定要停止吗？</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => {
              void stopTranslation(currentProject?.id);
              setCurrentStep('取消中');
            }}>
              确定停止
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 开始全文翻译确认对话框 */}
      <AlertDialog open={showStartDialog} onOpenChange={setShowStartDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>开始全文翻译</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingStartMethod === TranslationMethod.FOUR_STEP
                ? '确定要使用四步法翻译全文吗？系统会先做术语预检，再进行分析、初稿、批评和修订。'
                : '确定要开始全文翻译吗？系统会先做术语预检，再进行普通全文翻译。'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={async () => {
              setCurrentStep('术语预检中...');
              setIsPreparingFullTranslate(true);
              try {
                const intercepted = await prepareTermReviewIfNeeded(
                  pendingStartMethod,
                  pendingStartModel
                );
                setIsPreparingFullTranslate(false);
                if (intercepted) { setCurrentStep(null); return; }
                await runFullTranslate(pendingStartMethod, pendingStartModel);
              } catch (error) {
                console.error('Failed to start full translation:', error);
                toast.error('启动全文翻译失败，请重试');
                setCurrentStep(null);
                setIsPreparingFullTranslate(false);
              }
            }}>
              开始翻译
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
