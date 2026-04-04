import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { glossaryApi } from '../confirmation/api/glossaryApi';
import type { TermReviewDecision, TermReviewPayload } from '../confirmation/types';
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
import { Button } from '@/components/ui/button-extended';
import { DocumentSidebar } from './components/DocumentSidebar';
import { EditPanel } from './components/EditPanel';
import { NewProjectModal } from './components/NewProjectModal';
import { SectionView } from './components/SectionView';
import { WelcomeScreen } from './components/WelcomeScreen';
import { useFullTranslate, useProject, useSection } from './hooks';
import { fullTranslationService } from './services/fullTranslationService';
import type { TermConflictData } from './services/fullTranslationService';

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

type DocumentView = 'glossary' | 'term-review' | null;

interface PendingTranslationRequest {
  method: TranslationMethod;
}

function LazyPanelFallback() {
  return (
    <div className="flex min-h-[220px] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
    </div>
  );
}

export function DocumentFeature() {
  const [searchParams, setSearchParams] = useSearchParams();
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
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [immersiveTargetParagraphId, setImmersiveTargetParagraphId] = useState<string | null>(null);
  const [pendingTermReview, setPendingTermReview] = useState<TermReviewPayload | null>(null);
  const [pendingTranslationRequest, setPendingTranslationRequest] =
    useState<PendingTranslationRequest | null>(null);
  const [isSubmittingTermReview, setIsSubmittingTermReview] = useState(false);
  const [isPreparingFullTranslate, setIsPreparingFullTranslate] = useState(false);

  // AlertDialog 状态
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [showStartDialog, setShowStartDialog] = useState(false);
  const [pendingStartMethod, setPendingStartMethod] = useState<TranslationMethod>(TranslationMethod.FOUR_STEP);

  // 术语冲突对话框状态
  const [conflictDialogOpen, setConflictDialogOpen] = useState(false);
  const [currentConflict, setCurrentConflict] = useState<TermConflictData | null>(null);
  const [conflictResolver, setConflictResolver] = useState<{
    resolve: (value: { chosenTranslation: string; applyToAll: boolean }) => void;
  } | null>(null);

  // 注册术语冲突回调
  useEffect(() => {
    fullTranslationService.setTermConflictCallback(async (conflict) => {
      return new Promise((resolve) => {
        setCurrentConflict(conflict);
        setConflictDialogOpen(true);
        setConflictResolver({ resolve });
      });
    });
    return () => {
      fullTranslationService.setTermConflictCallback(null);
    };
  }, []);

  const isFullTranslating = useDocumentStore(state => state.isFullTranslating);
  const fullTranslateProgress = useDocumentStore(state => state.fullTranslateProgress);

  useProject(currentProject?.id ?? '');

  const isImmersiveMode = searchParams.get('immersive') === '1';
  const activeView = (searchParams.get('view') as DocumentView) || null;

  const setView = useCallback(
    (view: DocumentView) => {
      const next = new URLSearchParams(searchParams);
      if (view) {
        next.set('view', view);
      } else {
        next.delete('view');
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams]
  );

  useEffect(() => {
    setPendingTermReview(null);
    setPendingTranslationRequest(null);
    setIsPreparingFullTranslate(false);
  }, [currentProject?.id]);

  useEffect(() => {
    if (activeView === 'term-review' && !pendingTermReview) {
      setView(null);
    }
  }, [activeView, pendingTermReview, setView]);

  const activeSectionId = useMemo(() => {
    const fallbackSectionId = isImmersiveMode ? currentSection?.section_id ?? null : null;
    const candidateSectionId = selectedSectionId ?? fallbackSectionId;
    if (!candidateSectionId) return null;
    return sections.some(section => section.section_id === candidateSectionId) ||
      candidateSectionId === currentSection?.section_id
      ? candidateSectionId
      : null;
  }, [currentSection, isImmersiveMode, selectedSectionId, sections]);

  const {
    isLoading: sectionLoading,
    data: sectionData,
    refetch: refetchSection,
  } = useSection(currentProject?.id ?? '', activeSectionId ?? '');

  const { startTranslation, stopTranslation } = useFullTranslate();

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
      const next = new URLSearchParams(searchParams);
      if (enabled) {
        next.set('immersive', '1');
      } else {
        next.delete('immersive');
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams]
  );

  const handleSelectSection = useCallback(
    (section: Section) => {
      setSelectedSectionId(section.section_id);
      setCurrentSection(section);
      setCurrentParagraph(null);
      setImmersiveMode(false);
      if (activeView) {
        setView(null);
      }
    },
    [activeView, setCurrentParagraph, setCurrentSection, setImmersiveMode, setView]
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

  const runFullTranslate = useCallback(
    async (method: TranslationMethod = TranslationMethod.FOUR_STEP) => {
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
          if (activeSectionId) {
            refetchSection();
          }
        },
        methodType
      );
    },
    [activeSectionId, currentProject, refetchSection, startTranslation]
  );

  const prepareTermReviewIfNeeded = useCallback(
    async (method: TranslationMethod = TranslationMethod.FOUR_STEP) => {
      if (!currentProject) return false;

      try {
        const review = await glossaryApi.prepareTermReview(currentProject.id);
        if (review.review_required && review.total_candidates > 0) {
          setPendingTermReview(review);
          setPendingTranslationRequest({ method });
          setView('term-review');
          toast.info(`检测到 ${review.total_candidates} 个高优先级新术语，先确认再开始全文翻译`);
          return true;
        }
      } catch (error) {
        console.error('Failed to prepare term review:', error);
        toast.warning('术语预检失败，已跳过并直接开始全文翻译');
      }

      return false;
    },
    [currentProject, setView]
  );

  const handleFullTranslate = useCallback(
    async (method?: TranslationMethod) => {
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
      setShowStartDialog(true);
    },
    [
      currentProject,
      isFullTranslating,
      isPreparingFullTranslate,
      prepareTermReviewIfNeeded,
      runFullTranslate,
      stopTranslation,
    ]
  );

  const handleSubmitTermReview = useCallback(
    async (decisions: TermReviewDecision[]) => {
      if (!currentProject || !pendingTranslationRequest) {
        return;
      }

      setIsSubmittingTermReview(true);
      try {
        await glossaryApi.submitTermReview(currentProject.id, decisions);
        await glossaryApi.getProjectGlossary(currentProject.id);
        setPendingTermReview(null);
        setView(null);
        toast.success('术语预检已保存，开始全文翻译');
        await runFullTranslate(
          pendingTranslationRequest.method
        );
      } catch (error) {
        console.error('Failed to submit term review:', error);
        toast.error('保存术语预检失败');
      } finally {
        setIsSubmittingTermReview(false);
      }
    },
    [currentProject, pendingTranslationRequest, runFullTranslate, setView]
  );

  const handleCancelTermReview = useCallback(() => {
    setPendingTermReview(null);
    setPendingTranslationRequest(null);
    setView(null);
  }, [setView]);

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
      return <WelcomeScreen />;
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

  return (
    <div className="flex h-full overflow-auto">
      <DocumentSidebar
        sections={sections}
        activeSectionId={activeSectionId}
        onSectionSelect={handleSelectSectionById}
        onNewProject={() => setIsNewProjectModalOpen(true)}
        onFullTranslate={handleFullTranslate}
        isFullTranslating={isFullTranslating}
        isPreparingFullTranslate={isPreparingFullTranslate}
        fullTranslateProgress={fullTranslateProgress}
        currentStep={currentStep}
        projectId={currentProject?.id}
      />

      <main className="flex-1 overflow-y-auto">{renderMainContent()}</main>

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
          // 用户点遮罩/Escape 关闭时，默认保留现有翻译以避免 Promise 永远挂起
          if (conflictResolver && currentConflict) {
            conflictResolver.resolve({
              chosenTranslation: currentConflict.existing_translation,
              applyToAll: true,
            });
          }
          setConflictDialogOpen(false);
          setCurrentConflict(null);
          setConflictResolver(null);
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
                    conflictResolver?.resolve({
                      chosenTranslation: currentConflict.existing_translation,
                      applyToAll: true,
                    });
                    setConflictDialogOpen(false);
                    setCurrentConflict(null);
                    setConflictResolver(null);
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
                    conflictResolver?.resolve({
                      chosenTranslation: currentConflict.new_translation,
                      applyToAll: true,
                    });
                    setConflictDialogOpen(false);
                    setCurrentConflict(null);
                    setConflictResolver(null);
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
            <AlertDialogAction onClick={() => { stopTranslation(); setCurrentStep(null); }}>
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
                const intercepted = await prepareTermReviewIfNeeded(pendingStartMethod);
                setIsPreparingFullTranslate(false);
                if (intercepted) { setCurrentStep(null); return; }
                await runFullTranslate(pendingStartMethod);
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
