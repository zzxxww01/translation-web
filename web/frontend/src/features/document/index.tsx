import { useState, useCallback, useMemo } from 'react';
import { useDocumentStore } from '../../shared/stores';
import { useSection, useFullTranslate, useProject } from './hooks';
import { documentApi } from './api';
import { DocumentSidebar } from './components/DocumentSidebar';
import { WelcomeScreen } from './components/WelcomeScreen';
import { SectionView } from './components/SectionView';
import { EditPanel } from './components/EditPanel';
import { NewProjectModal } from './components/NewProjectModal';
import { TranslationMethod } from '../../shared/constants';
import type { Paragraph, Section } from '../../shared/types';

export function DocumentFeature() {
  const {
    currentProject,
    setCurrentProject,
    currentSection,
    currentParagraph,
    sections,
    setSections,
    setCurrentParagraph,
  } = useDocumentStore();

  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string | null>(null);

  const isFullTranslating = useDocumentStore(state => state.isFullTranslating);
  const fullTranslateProgress = useDocumentStore(state => state.fullTranslateProgress);

  useProject(currentProject?.id ?? '');

  const activeSectionId = useMemo(() => {
    if (!selectedSectionId) return null;
    return sections.some(section => section.section_id === selectedSectionId)
      ? selectedSectionId
      : null;
  }, [selectedSectionId, sections]);

  const {
    isLoading: sectionLoading,
    data: sectionData,
    refetch: refetchSection,
  } = useSection(currentProject?.id ?? '', activeSectionId ?? '');

  const { startTranslation, stopTranslation } = useFullTranslate();

  const displaySection = useMemo(() => sectionData || currentSection, [sectionData, currentSection]);

  const handleSelectSection = useCallback(
    (section: Section) => {
      setSelectedSectionId(section.section_id);
      setCurrentParagraph(null);
    },
    [setCurrentParagraph]
  );

  const handleSelectSectionById = useCallback(
    (sectionId: string) => {
      const section = sections.find(s => s.section_id === sectionId);
      if (section) {
        handleSelectSection(section);
      }
    },
    [sections, handleSelectSection]
  );

  const handleSelectParagraph = useCallback(
    (paragraph: Paragraph) => {
      setCurrentParagraph(paragraph);
    },
    [setCurrentParagraph]
  );

  const getCurrentParagraphIndex = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return -1;
    return displaySection.paragraphs.findIndex(p => p.id === currentParagraph.id);
  }, [displaySection, currentParagraph]);

  const handleNextParagraph = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return;

    const currentIndex = getCurrentParagraphIndex();

    if (currentIndex < displaySection.paragraphs.length - 1) {
      const nextParagraph = displaySection.paragraphs[currentIndex + 1];
      setCurrentParagraph(nextParagraph);
      return;
    }

    setCurrentParagraph(null);
  }, [displaySection, currentParagraph, getCurrentParagraphIndex, setCurrentParagraph]);

  const handlePrevParagraph = useCallback(() => {
    if (!displaySection?.paragraphs || !currentParagraph) return;

    const currentIndex = getCurrentParagraphIndex();
    if (currentIndex > 0) {
      const prevParagraph = displaySection.paragraphs[currentIndex - 1];
      setCurrentParagraph(prevParagraph);
    }
  }, [displaySection, currentParagraph, getCurrentParagraphIndex, setCurrentParagraph]);

  const handleFullTranslate = useCallback(
    async (model?: string, method?: TranslationMethod) => {
      if (!currentProject) return;

      if (isFullTranslating) {
        if (!confirm('翻译正在进行中，确定要停止吗？')) {
          return;
        }
        stopTranslation();
        setCurrentStep(null);
        return;
      }

      const confirmMessage =
        method === TranslationMethod.FOUR_STEP
          ? '确定要使用四步法翻译全文吗？\n\n四步法会进行深度分析、反思和润色，质量更高但耗时更长。'
          : '确定要一键翻译全文吗？这可能需要较长时间。';

      if (!confirm(confirmMessage)) {
        return;
      }

      setCurrentStep(null);

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
    [
      currentProject,
      isFullTranslating,
      stopTranslation,
      startTranslation,
      activeSectionId,
      refetchSection,
    ]
  );

  const handleProjectCreated = useCallback(
    async (projectId: string) => {
      try {
        const projectData = await documentApi.getProject(projectId);
        setCurrentProject(projectData);
        setSections(projectData.sections ?? []);
      } catch (error) {
        console.error('Failed to load project:', error);
      }
    },
    [setCurrentProject, setSections]
  );

  const renderMainContent = () => {
    if (!currentProject) {
      return <WelcomeScreen />;
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
      />
    );
  };

  const currentIndex = getCurrentParagraphIndex();
  const totalCount = displaySection?.paragraphs?.length ?? 0;

  return (
    <div className="flex h-full overflow-auto">
      <DocumentSidebar
        sections={sections}
        activeSectionId={activeSectionId}
        onSectionSelect={handleSelectSectionById}
        onNewProject={() => setIsNewProjectModalOpen(true)}
        onFullTranslate={handleFullTranslate}
        isFullTranslating={isFullTranslating}
        fullTranslateProgress={fullTranslateProgress}
        currentStep={currentStep}
        projectId={currentProject?.id}
      />

      <main className="flex-1 overflow-y-auto">{renderMainContent()}</main>

      {currentParagraph && currentProject && activeSectionId && displaySection && (
        <EditPanel
          paragraph={currentParagraph}
          projectId={currentProject.id}
          sectionId={activeSectionId}
          onClose={() => setCurrentParagraph(null)}
          onNext={handleNextParagraph}
          onPrev={handlePrevParagraph}
          currentIndex={currentIndex}
          totalCount={totalCount}
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

