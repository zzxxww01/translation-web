import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import type { TermReviewDecision } from '../confirmation/types';
import { useDocumentStore } from '@/shared/stores';
import { TranslationMethod } from '@/shared/constants';
import type { Paragraph, Project, Section } from '@/shared/types';
import { documentApi } from './api';
import { isTranslationRunActive } from './translationStatus';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/Button';
import { PanelLeft } from 'lucide-react';
import { DocumentSidebar } from './components/DocumentSidebar';
import { EditPanel } from './components/EditPanel';
import { NewProjectModal } from './components/NewProjectModal';
import { SectionView } from './components/SectionView';
import { WelcomeScreen } from './components/WelcomeScreen';
import {
  useDocumentViewState,
  useFullTranslate,
  useProject,
  useProjects,
  useSection,
  useTermConflictDialog,
  useTermReviewFlow,
  useTranslationStatusSync,
} from './hooks';
import { findFirstUnresolvedParagraphId, findResumeSectionId } from './workflow';

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
  const currentProject = useDocumentStore(state => state.currentProject);
  const setCurrentProject = useDocumentStore(state => state.setCurrentProject);
  const resetCurrentProject = useDocumentStore(state => state.resetCurrentProject);
  const currentSection = useDocumentStore(state => state.currentSection);
  const setCurrentSection = useDocumentStore(state => state.setCurrentSection);
  const currentParagraph = useDocumentStore(state => state.currentParagraph);
  const setCurrentParagraph = useDocumentStore(state => state.setCurrentParagraph);
  const sections = useDocumentStore(state => state.sections);
  const setSections = useDocumentStore(state => state.setSections);

  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // AlertDialog 状态
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [showStartDialog, setShowStartDialog] = useState(false);
  const [pendingStartMethod, setPendingStartMethod] = useState<TranslationMethod>(TranslationMethod.FOUR_STEP);
  const [pendingStartModel, setPendingStartModel] = useState<string | undefined>(undefined);

  const isFullTranslating = useDocumentStore(state => state.isFullTranslating);
  const fullTranslateProgress = useDocumentStore(state => state.fullTranslateProgress);
  const fullTranslateProjectId = useDocumentStore(state => state.fullTranslateProjectId);
  const {
    activeProjectId,
    activeSectionId,
    activeParagraphId,
    requestedSectionId,
    activeView,
    isImmersiveMode,
    setView,
    updateRouteParams,
  } = useDocumentViewState({ sections });
  const { data: projects = [] } = useProjects();
  const {
    data: projectData,
    isLoading: projectLoading,
  } = useProject(activeProjectId ?? '');
  const activeProject =
    activeProjectId && currentProject?.id === activeProjectId
      ? currentProject
      : projectData ?? null;
  const hasLocalRunForCurrentProject = Boolean(
    isFullTranslating &&
      activeProject?.id &&
      fullTranslateProjectId === activeProject.id
  );

  useEffect(() => {
    if (!activeProjectId || !projectData || projectData.id !== activeProjectId) return;
    setCurrentProject(projectData);
    setSections(projectData.sections ?? []);
  }, [activeProjectId, projectData, setCurrentProject, setSections]);

  useEffect(() => {
    if (!activeProjectId || !projectData) return;
    const projectSections = projectData.sections ?? [];
    const requestedSectionExists =
      requestedSectionId &&
      projectSections.some(section => section.section_id === requestedSectionId);
    if (requestedSectionExists || projectSections.length === 0) return;

    updateRouteParams(
      {
        sectionId: findResumeSectionId(projectSections),
        paragraphId: null,
        mode: null,
      },
      { replace: true }
    );
  }, [activeProjectId, projectData, requestedSectionId, updateRouteParams]);

  const {
    backendTranslationStatus,
    currentStep,
    setCurrentStep,
  } = useTranslationStatusSync(activeProject?.id);
  const hasActiveBackendRunForCurrentProject = isTranslationRunActive(
    backendTranslationStatus,
    activeProject?.id
  );
  const isCurrentProjectFullTranslating =
    hasLocalRunForCurrentProject || hasActiveBackendRunForCurrentProject;
  const {
    closeWithDefaultResolution,
    conflictDialogOpen,
    currentConflict,
    resolveConflict,
  } = useTermConflictDialog();

  const {
    isLoading: sectionLoading,
    data: sectionData,
  } = useSection(activeProject?.id ?? '', activeSectionId ?? '');

  useEffect(() => {
    if (!sectionData || sectionData.section_id !== activeSectionId) return;
    setCurrentSection(sectionData);
  }, [activeSectionId, sectionData, setCurrentSection]);

  const { stopTranslation } = useFullTranslate();

  const {
    cancelTermReview,
    isPreparingFullTranslate,
    isSubmittingTermReview,
    pendingTermReview,
    termReviewTimeoutSeconds,
    prepareTermReviewIfNeeded,
    submitTermReview,
  } = useTermReviewFlow({
    currentProjectId: activeProject?.id,
    activeRunId: backendTranslationStatus?.active_run_id,
    setView,
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

  useEffect(() => {
    if (!displaySection?.paragraphs || isImmersiveMode) {
      if (isImmersiveMode && currentParagraph) {
        setCurrentParagraph(null);
      }
      return;
    }

    if (!activeParagraphId) {
      if (currentParagraph) setCurrentParagraph(null);
      return;
    }

    const paragraph = displaySection.paragraphs.find(item => item.id === activeParagraphId);
    if (!paragraph) {
      updateRouteParams({ paragraphId: null }, { replace: true });
      setCurrentParagraph(null);
      return;
    }
    if (currentParagraph?.id !== paragraph.id || currentParagraph !== paragraph) {
      setCurrentParagraph(paragraph);
    }
  }, [
    activeParagraphId,
    currentParagraph,
    displaySection,
    isImmersiveMode,
    setCurrentParagraph,
    updateRouteParams,
  ]);

  const handleSelectSection = useCallback(
    (section: Section) => {
      setCurrentSection(section);
      setCurrentParagraph(null);
      updateRouteParams({
        sectionId: section.section_id,
        paragraphId: null,
        mode: null,
        view: activeView ? null : undefined,
      });
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

  const handleSelectParagraph = useCallback(
    (paragraph: Paragraph) => {
      const useFullScreenEditor =
        typeof window !== 'undefined' &&
        window.matchMedia('(max-width: 767px)').matches;
      if (useFullScreenEditor) {
        setCurrentParagraph(null);
        updateRouteParams({ paragraphId: paragraph.id, mode: 'immersive' });
        return;
      }
      setCurrentParagraph(paragraph);
      updateRouteParams({ paragraphId: paragraph.id, mode: null });
    },
    [setCurrentParagraph, updateRouteParams]
  );

  const handleEnterImmersive = useCallback(() => {
    if (displaySection) {
      setCurrentSection(displaySection);
    }
    const immersiveTargetParagraphId =
      currentParagraph?.id ??
      activeParagraphId ??
      findFirstUnresolvedParagraphId(displaySection?.paragraphs ?? []);
    setCurrentParagraph(null);
    updateRouteParams({ paragraphId: immersiveTargetParagraphId, mode: 'immersive' });
  }, [
    activeParagraphId,
    currentParagraph,
    displaySection,
    setCurrentParagraph,
    setCurrentSection,
    updateRouteParams,
  ]);

  const handleExitImmersive = useCallback(() => {
    updateRouteParams({ paragraphId: null, mode: null });
  }, [updateRouteParams]);

  const handleCloseEditPanel = useCallback(() => {
    setCurrentParagraph(null);
    updateRouteParams({ paragraphId: null });
  }, [setCurrentParagraph, updateRouteParams]);

  const getCurrentParagraphIndex = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return -1;
    return displaySection.paragraphs.findIndex(paragraph => paragraph.id === currentParagraph.id);
  }, [displaySection, currentParagraph]);

  const handleNextParagraph = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return;

    const currentIndex = getCurrentParagraphIndex();
    if (currentIndex < displaySection.paragraphs.length - 1) {
      const nextParagraph = displaySection.paragraphs[currentIndex + 1];
      setCurrentParagraph(nextParagraph);
      updateRouteParams({ paragraphId: nextParagraph.id });
      return;
    }

    handleCloseEditPanel();
  }, [
    currentParagraph,
    displaySection,
    getCurrentParagraphIndex,
    handleCloseEditPanel,
    setCurrentParagraph,
    updateRouteParams,
  ]);

  const handlePrevParagraph = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return;

    const currentIndex = getCurrentParagraphIndex();
    if (currentIndex > 0) {
      const previousParagraph = displaySection.paragraphs[currentIndex - 1];
      setCurrentParagraph(previousParagraph);
      updateRouteParams({ paragraphId: previousParagraph.id });
    }
  }, [
    currentParagraph,
    displaySection,
    getCurrentParagraphIndex,
    setCurrentParagraph,
    updateRouteParams,
  ]);

  const handleFullTranslate = useCallback(
    async (method?: TranslationMethod, model?: string) => {
      if (!activeProject) return;

      if (isPreparingFullTranslate) {
        toast.info('术语预检进行中，请稍候');
        return;
      }

      if (isCurrentProjectFullTranslating) {
        setShowStopDialog(true);
        return;
      }

      const selectedMethod = method ?? TranslationMethod.FOUR_STEP;
      setPendingStartMethod(selectedMethod);
      setPendingStartModel(model);
      setShowStartDialog(true);
    },
    [
      activeProject,
      isCurrentProjectFullTranslating,
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
        const createdProject = await documentApi.getProject(projectId);
        setCurrentProject(createdProject);
        setSections(createdProject.sections ?? []);
        updateRouteParams({
          projectId: createdProject.id,
          sectionId: findResumeSectionId(createdProject.sections ?? []),
          paragraphId: null,
          mode: null,
          view: null,
        });
      } catch (error) {
        console.error('Failed to load project:', error);
      }
    },
    [setCurrentProject, setSections, updateRouteParams]
  );

  const handleSelectProject = useCallback(
    (project: Project) => {
      setCurrentProject(project);
      updateRouteParams({
        projectId: project.id,
        sectionId: null,
        paragraphId: null,
        mode: null,
        view: null,
      });
    },
    [setCurrentProject, updateRouteParams]
  );

  const handleProjectDeleted = useCallback(() => {
    resetCurrentProject();
    updateRouteParams({
      projectId: null,
      sectionId: null,
      paragraphId: null,
      mode: null,
      view: null,
    });
  }, [resetCurrentProject, updateRouteParams]);

  const renderMainContent = () => {
    if (!activeProjectId) {
      return (
        <WelcomeScreen
          projects={projects}
          lastProjectId={activeProjectId}
          onSelectProject={handleSelectProject}
          onNewProject={() => setIsNewProjectModalOpen(true)}
        />
      );
    }

    if (projectLoading && !activeProject) {
      return (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
        </div>
      );
    }

    if (!activeProject) {
      return (
        <div className="mx-auto max-w-3xl py-12 text-center">
          <h2 className="text-lg font-semibold">无法加载该项目</h2>
          <p className="mt-2 text-sm text-text-muted">项目可能已被删除，或当前暂时无法访问。</p>
          <Button type="button" variant="outline" className="mt-4" onClick={handleProjectDeleted}>
            返回项目列表
          </Button>
        </div>
      );
    }

    if (activeView === 'glossary') {
      return (
        <Suspense fallback={<LazyPanelFallback />}>
          <GlossaryCenter
            projectId={activeProject.id}
            projectTitle={activeProject.title}
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
            key={pendingTermReview.artifact_id}
            review={pendingTermReview}
            isSubmitting={isSubmittingTermReview}
            autoContinueSeconds={termReviewTimeoutSeconds}
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
            <h2 className="text-xl font-bold">{activeProject.title}</h2>
            <p className="text-text-muted">请选择一个章节开始翻译</p>
          </div>
        </div>
      );
    }

    // N12: 切到未缓存章节时，selectedSection 只是不含 paragraphs 的摘要，
    // displaySection 为真值会跳过加载分支并闪现空段落。
    // 因此只要还没有 paragraphs 且正在加载，就继续显示加载骨架。
    if ((!displaySection || !displaySection.paragraphs) && sectionLoading) {
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
            <h2 className="text-xl font-bold">{activeProject.title}</h2>
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
  const effectiveProgress = hasActiveBackendRunForCurrentProject
    ? {
        current: backendTranslationStatus?.translated_paragraphs || 0,
        total: backendTranslationStatus?.total_paragraphs || 0,
      }
    : hasLocalRunForCurrentProject
      ? fullTranslateProgress
      : null;
  const effectiveIsCancelling = Boolean(
    hasActiveBackendRunForCurrentProject &&
      backendTranslationStatus?.is_cancelling
  );
  const effectiveIsFullTranslating = Boolean(
    hasActiveBackendRunForCurrentProject || hasLocalRunForCurrentProject
  );
  const effectiveCurrentStep =
    (hasActiveBackendRunForCurrentProject &&
      backendTranslationStatus?.current_step) ||
    (hasLocalRunForCurrentProject ? currentStep : null);

  const renderSidebar = (mobile: boolean) => (
    <DocumentSidebar
      sections={sections}
      activeSectionId={activeSectionId}
      onSectionSelect={handleSelectSectionById}
      selectedProjectId={activeProject?.id}
      onProjectSelect={handleSelectProject}
      onProjectDeleted={handleProjectDeleted}
      onNewProject={() => setIsNewProjectModalOpen(true)}
      onFullTranslate={handleFullTranslate}
      onStopTranslate={() => setShowStopDialog(true)}
      isFullTranslating={effectiveIsFullTranslating}
      isCancelling={effectiveIsCancelling}
      isPreparingFullTranslate={isPreparingFullTranslate}
      onCancelTermReview={handleCancelTermReview}
      fullTranslateProgress={effectiveProgress}
      currentStep={effectiveCurrentStep}
      activeTranslationProjectId={
        backendTranslationStatus?.active_project_id ||
        (isFullTranslating ? fullTranslateProjectId : null)
      }
      projectId={activeProject?.id}
      className={mobile ? 'w-full border-r-0' : 'hidden md:flex'}
      onNavigate={mobile ? () => setMobileSidebarOpen(false) : undefined}
    />
  );

  return (
    <div className="flex h-full min-h-0 overflow-hidden">
      {renderSidebar(false)}

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border-subtle bg-bg-secondary px-3 md:hidden">
          <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
            <SheetTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="打开文档导航"
                title="文档导航"
              >
                <PanelLeft className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[min(90vw,22rem)] p-0 pt-10">
              <SheetHeader className="sr-only">
                <SheetTitle>文档导航</SheetTitle>
                <SheetDescription>选择项目和章节，查看进度并执行全文操作。</SheetDescription>
              </SheetHeader>
              {renderSidebar(true)}
            </SheetContent>
          </Sheet>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">
              {currentSection?.title || activeProject?.title || '文档工作台'}
            </p>
            {activeProject && currentSection && (
              <p className="truncate text-xs text-text-muted">{activeProject.title}</p>
            )}
          </div>
        </div>

        <main className="min-w-0 flex-1 overflow-y-auto">{renderMainContent()}</main>
      </div>

      {showEditingPanels && currentParagraph && activeProject && activeSectionId && displaySection && (
        <EditPanel
          paragraph={currentParagraph}
          projectId={activeProject.id}
          sectionId={activeSectionId}
          onClose={() => setCurrentParagraph(null)}
          onNext={handleNextParagraph}
          onPrev={handlePrevParagraph}
          currentIndex={currentIndex}
          totalCount={totalCount}
          onEnterImmersive={handleEnterImmersive}
        />
      )}

      {showEditingPanels && isImmersiveMode && activeProject && displaySection && (
        <Suspense fallback={<LazyPanelFallback />}>
          <ImmersiveEditor
            projectId={activeProject.id}
            section={displaySection}
            initialParagraphId={activeParagraphId ?? undefined}
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
              void stopTranslation(activeProject?.id);
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
              {' '}任务由后台持续运行，关闭浏览器不会中断；术语未在确认窗口内提交时会自动采用建议继续。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={async () => {
              try {
                await prepareTermReviewIfNeeded(
                  pendingStartMethod,
                  pendingStartModel
                );
              } catch (error) {
                console.error('Failed to start full translation:', error);
                toast.error('启动全文翻译失败，请重试');
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
