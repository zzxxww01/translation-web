import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useToast } from '../../components/ui';
import { glossaryApi } from '../confirmation/api/glossaryApi';
import type { TermReviewDecision, TermReviewPayload } from '../confirmation/types';
import { useDocumentStore } from '../../shared/stores';
import { TranslationMethod } from '../../shared/constants';
import type { Paragraph, Section } from '../../shared/types';
import { documentApi } from './api';
import { DocumentSidebar } from './components/DocumentSidebar';
import { EditPanel } from './components/EditPanel';
import { GlossaryManagementPage } from './components/GlossaryManagementPage';
import { ImmersiveEditor } from './components/ImmersiveEditor';
import { NewProjectModal } from './components/NewProjectModal';
import { SectionView } from './components/SectionView';
import { TerminologyReviewPage } from './components/TerminologyReviewPage';
import { WelcomeScreen } from './components/WelcomeScreen';
import { useFullTranslate, useProject, useSection } from './hooks';

type DocumentView = 'glossary' | 'term-review' | null;

interface PendingTranslationRequest {
  model?: string;
  method: TranslationMethod;
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
  const { showToast } = useToast();

  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [immersiveTargetParagraphId, setImmersiveTargetParagraphId] = useState<string | null>(null);
  const [pendingTermReview, setPendingTermReview] = useState<TermReviewPayload | null>(null);
  const [pendingTranslationRequest, setPendingTranslationRequest] =
    useState<PendingTranslationRequest | null>(null);
  const [isSubmittingTermReview, setIsSubmittingTermReview] = useState(false);

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
    async (model?: string, method: TranslationMethod = TranslationMethod.FOUR_STEP) => {
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
        model,
        methodType
      );
    },
    [activeSectionId, currentProject, refetchSection, startTranslation]
  );

  const prepareTermReviewIfNeeded = useCallback(
    async (model?: string, method: TranslationMethod = TranslationMethod.FOUR_STEP) => {
      if (!currentProject) return false;

      const review = await glossaryApi.prepareTermReview(currentProject.id);
      if (review.review_required && review.total_candidates > 0) {
        setPendingTermReview(review);
        setPendingTranslationRequest({ model, method });
        setView('term-review');
        showToast(`检测到 ${review.total_candidates} 个高优先级新术语，先确认再开始全文翻译`, 'info');
        return true;
      }

      return false;
    },
    [currentProject, setView, showToast]
  );

  const handleFullTranslate = useCallback(
    async (model?: string, method?: TranslationMethod) => {
      if (!currentProject) return;

      if (isFullTranslating) {
        if (!window.confirm('翻译正在进行中，确定要停止吗？')) {
          return;
        }
        stopTranslation();
        setCurrentStep(null);
        return;
      }

      const selectedMethod = method ?? TranslationMethod.FOUR_STEP;
      const confirmMessage =
        selectedMethod === TranslationMethod.FOUR_STEP
          ? '确定要使用四步法翻译全文吗？\n\n系统会先做术语预检，再进行分析、初稿、批评和修订。'
          : '确定要开始全文翻译吗？\n\n系统会先做术语预检，再进行普通全文翻译。';

      if (!window.confirm(confirmMessage)) {
        return;
      }

      setCurrentStep(null);
      const intercepted = await prepareTermReviewIfNeeded(model, selectedMethod);
      if (!intercepted) {
        await runFullTranslate(model, selectedMethod);
      }
    },
    [
      currentProject,
      isFullTranslating,
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
        showToast('术语预检已保存，开始全文翻译', 'success');
        await runFullTranslate(
          pendingTranslationRequest.model,
          pendingTranslationRequest.method
        );
      } catch (error) {
        console.error('Failed to submit term review:', error);
        showToast('保存术语预检失败', 'error');
      } finally {
        setIsSubmittingTermReview(false);
      }
    },
    [currentProject, pendingTranslationRequest, runFullTranslate, setView, showToast]
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
        <GlossaryManagementPage
          projectId={currentProject.id}
          projectTitle={currentProject.title}
          onBack={() => setView(null)}
        />
      );
    }

    if (activeView === 'term-review' && pendingTermReview) {
      return (
        <TerminologyReviewPage
          review={pendingTermReview}
          isSubmitting={isSubmittingTermReview}
          onSubmit={handleSubmitTermReview}
          onCancel={handleCancelTermReview}
        />
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
        onOpenGlossaryManagement={() => setView('glossary')}
        isFullTranslating={isFullTranslating}
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
        <ImmersiveEditor
          projectId={currentProject.id}
          section={displaySection}
          initialParagraphId={immersiveTargetParagraphId}
          onClose={handleExitImmersive}
        />
      )}

      <NewProjectModal
        isOpen={isNewProjectModalOpen}
        onClose={() => setIsNewProjectModalOpen(false)}
        onProjectCreated={handleProjectCreated}
      />
    </div>
  );
}
