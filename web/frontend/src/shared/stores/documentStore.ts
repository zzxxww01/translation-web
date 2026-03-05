/**
 * 长文翻译状态管理
 * 使用 Zustand 管理文档翻译相关的状态
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Project, Section, Paragraph } from '../types';
import { STORAGE_KEYS } from '../constants';

/**
 * 长文翻译状态接口
 */
interface DocumentState {
  // 当前选中的项目
  currentProject: Project | null;
  // 当前选中的章节
  currentSection: Section | null;
  // 当前选中的段落
  currentParagraph: Paragraph | null;
  // 项目列表
  projects: Project[];
  // 当前项目的章节列表
  sections: Section[];
  // 是否正在处理
  isProcessing: boolean;
  // 错误信息
  error: string | null;

  // 全文翻译状态（持久化，跨tab切换保持）
  isFullTranslating: boolean;
  fullTranslateProgress: { current: number; total: number } | null;
  fullTranslateProjectId: string | null;
}

/**
 * 长文翻译操作接口
 */
interface DocumentActions {
  // 设置操作
  setCurrentProject: (project: Project | null) => void;
  setCurrentSection: (section: Section | null) => void;
  setCurrentParagraph: (paragraph: Paragraph | null) => void;
  setProjects: (projects: Project[]) => void;
  setSections: (sections: Section[]) => void;
  setProcessing: (isProcessing: boolean) => void;
  setError: (error: string | null) => void;

  // 更新操作
  updateProject: (projectId: string, updates: Partial<Project>) => void;
  updateSection: (sectionId: string, updates: Partial<Section>) => void;
  updateParagraph: (paragraphId: string, updates: Partial<Paragraph>) => void;
  updateParagraphInSection: (
    sectionId: string,
    paragraphId: string,
    updates: Partial<Paragraph>
  ) => void;

  // 批量操作
  updateMultipleParagraphs: (
    sectionId: string,
    paragraphIds: string[],
    updates: Partial<Paragraph>
  ) => void;

  // 全文翻译状态操作
  setFullTranslating: (isTranslating: boolean) => void;
  setFullTranslateProgress: (progress: { current: number; total: number } | null) => void;
  setFullTranslateProjectId: (projectId: string | null) => void;
  startFullTranslate: (projectId: string, total: number) => void;
  updateFullTranslateProgress: (current: number) => void;
  endFullTranslate: () => void;

  // 导航操作
  goToNextSection: () => boolean;
  goToPreviousSection: () => boolean;
  goToNextParagraph: () => boolean;
  goToPreviousParagraph: () => boolean;

  // 重置
  reset: () => void;
  resetCurrentProject: () => void;
}

/**
 * 初始状态
 */
const initialState: DocumentState = {
  currentProject: null,
  currentSection: null,
  currentParagraph: null,
  projects: [],
  sections: [],
  isProcessing: false,
  error: null,
  isFullTranslating: false,
  fullTranslateProgress: null,
  fullTranslateProjectId: null,
};

export type DocumentStore = DocumentState & DocumentActions;

/**
 * 创建文档 Store
 */
export const useDocumentStore = create<DocumentStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // 设置操作
        setCurrentProject: project =>
          set({ currentProject: project }, false, 'setCurrentProject'),

        setCurrentSection: section =>
          set({ currentSection: section }, false, 'setCurrentSection'),

        setCurrentParagraph: paragraph =>
          set({ currentParagraph: paragraph }, false, 'setCurrentParagraph'),

        setProjects: projects => set({ projects }, false, 'setProjects'),

        setSections: sections => set({ sections }, false, 'setSections'),

        setProcessing: isProcessing =>
          set({ isProcessing }, false, 'setProcessing'),

        setError: error => set({ error }, false, 'setError'),

        // 更新操作
        updateProject: (projectId, updates) =>
          set(
            state => ({
              projects: state.projects.map(p =>
                p.id === projectId ? { ...p, ...updates } : p
              ),
              currentProject:
                state.currentProject?.id === projectId
                  ? { ...state.currentProject, ...updates }
                  : state.currentProject,
            }),
            false,
            'updateProject'
          ),

        updateSection: (sectionId, updates) =>
          set(
            state => ({
              sections: state.sections.map(s =>
                s.section_id === sectionId ? { ...s, ...updates } : s
              ),
              currentSection:
                state.currentSection?.section_id === sectionId
                  ? { ...state.currentSection, ...updates }
                  : state.currentSection,
            }),
            false,
            'updateSection'
          ),

        updateParagraph: (paragraphId, updates) =>
          set(
            state => {
              if (!state.currentSection?.paragraphs) return state;

              const updatedParagraphs = state.currentSection.paragraphs.map(p =>
                p.id === paragraphId ? { ...p, ...updates } : p
              );

              return {
                currentSection: {
                  ...state.currentSection,
                  paragraphs: updatedParagraphs,
                },
                currentParagraph:
                  state.currentParagraph?.id === paragraphId
                    ? { ...state.currentParagraph, ...updates }
                    : state.currentParagraph,
              };
            },
            false,
            'updateParagraph'
          ),

        updateParagraphInSection: (sectionId, paragraphId, updates) =>
          set(
            state => {
              const mergeParagraph = (paragraph: Paragraph) =>
                paragraph.id === paragraphId ? { ...paragraph, ...updates } : paragraph;

              // 更新 sections 中已加载 paragraphs 的 section
              const updatedSections = state.sections.map(section => {
                if (section.section_id !== sectionId || !section.paragraphs) {
                  return section;
                }
                return {
                  ...section,
                  paragraphs: section.paragraphs.map(mergeParagraph),
                };
              });

              // 优先更新 currentSection，避免被 sections 里的“摘要 section”覆盖
              const updatedCurrentSectionWithParagraphs =
                state.currentSection?.section_id === sectionId && state.currentSection.paragraphs
                  ? {
                      ...state.currentSection,
                      paragraphs: state.currentSection.paragraphs.map(mergeParagraph),
                    }
                  : state.currentSection;

              const updatedCurrentSection =
                state.currentSection?.section_id === sectionId && !state.currentSection.paragraphs
                  ? updatedSections.find(section => section.section_id === sectionId) ||
                    state.currentSection
                  : updatedCurrentSectionWithParagraphs;

              const updatedCurrentParagraph =
                state.currentParagraph?.id === paragraphId
                  ? { ...state.currentParagraph, ...updates }
                  : state.currentParagraph;

              return {
                sections: updatedSections,
                currentSection: updatedCurrentSection,
                currentParagraph: updatedCurrentParagraph,
              };
            },
            false,
            'updateParagraphInSection'
          ),

        // 批量操作
        updateMultipleParagraphs: (sectionId, paragraphIds, updates) =>
          set(
            state => {
              const updatedSections = state.sections.map(section => {
                if (section.section_id === sectionId && section.paragraphs) {
                  return {
                    ...section,
                    paragraphs: section.paragraphs.map(p =>
                      paragraphIds.includes(p.id) ? { ...p, ...updates } : p
                    ),
                  };
                }
                return section;
              });

              return {
                sections: updatedSections,
                currentSection:
                  state.currentSection?.section_id === sectionId
                    ? updatedSections.find(s => s.section_id === sectionId) ||
                      state.currentSection
                    : state.currentSection,
              };
            },
            false,
            'updateMultipleParagraphs'
          ),

        // 导航操作
        goToNextSection: () => {
          const state = get();
          if (!state.currentSection || state.sections.length === 0) return false;

          const currentIndex = state.sections.findIndex(
            s => s.section_id === state.currentSection?.section_id
          );

          if (currentIndex < state.sections.length - 1) {
            set({ currentSection: state.sections[currentIndex + 1] }, false, 'goToNextSection');
            return true;
          }

          return false;
        },

        goToPreviousSection: () => {
          const state = get();
          if (!state.currentSection || state.sections.length === 0) return false;

          const currentIndex = state.sections.findIndex(
            s => s.section_id === state.currentSection?.section_id
          );

          if (currentIndex > 0) {
            set(
              { currentSection: state.sections[currentIndex - 1] },
              false,
              'goToPreviousSection'
            );
            return true;
          }

          return false;
        },

        goToNextParagraph: () => {
          const state = get();
          const paragraphs = state.currentSection?.paragraphs;
          if (!state.currentParagraph || !paragraphs?.length) return false;

          const currentIndex = paragraphs.findIndex(
            p => p.id === state.currentParagraph?.id
          );

          if (currentIndex < paragraphs.length - 1) {
            set(
              { currentParagraph: paragraphs[currentIndex + 1] },
              false,
              'goToNextParagraph'
            );
            return true;
          }

          return false;
        },

        goToPreviousParagraph: () => {
          const state = get();
          const paragraphs = state.currentSection?.paragraphs;
          if (!state.currentParagraph || !paragraphs?.length) return false;

          const currentIndex = paragraphs.findIndex(
            p => p.id === state.currentParagraph?.id
          );

          if (currentIndex > 0) {
            set(
              { currentParagraph: paragraphs[currentIndex - 1] },
              false,
              'goToPreviousParagraph'
            );
            return true;
          }

          return false;
        },

        // 全文翻译状态操作
        setFullTranslating: (isTranslating) =>
          set({ isFullTranslating: isTranslating }, false, 'setFullTranslating'),

        setFullTranslateProgress: (progress) =>
          set({ fullTranslateProgress: progress }, false, 'setFullTranslateProgress'),

        setFullTranslateProjectId: (projectId) =>
          set({ fullTranslateProjectId: projectId }, false, 'setFullTranslateProjectId'),

        startFullTranslate: (projectId, total) =>
          set(
            {
              isFullTranslating: true,
              fullTranslateProgress: { current: 0, total },
              fullTranslateProjectId: projectId,
            },
            false,
            'startFullTranslate'
          ),

        updateFullTranslateProgress: (current) =>
          set(
            state => ({
              fullTranslateProgress: state.fullTranslateProgress
                ? { ...state.fullTranslateProgress, current }
                : null,
            }),
            false,
            'updateFullTranslateProgress'
          ),

        endFullTranslate: () =>
          set(
            {
              isFullTranslating: false,
              fullTranslateProgress: null,
              fullTranslateProjectId: null,
            },
            false,
            'endFullTranslate'
          ),

        // 重置操作
        reset: () => set(initialState, false, 'reset'),

        resetCurrentProject: () =>
          set(
            {
              currentProject: null,
              currentSection: null,
              currentParagraph: null,
              sections: [],
              error: null,
            },
            false,
            'resetCurrentProject'
          ),
      }),
      {
        name: STORAGE_KEYS.DOCUMENT_STATE,
        // 只持久化必要的状态
        partialize: state => ({
          currentProject: state.currentProject,
          currentSection: state.currentSection,
          sections: state.sections,
        }),
      }
    ),
    { name: 'DocumentStore' }
  )
);

/**
 * 选择器 hooks
 */
export const useCurrentProject = () => useDocumentStore(state => state.currentProject);
export const useCurrentSection = () => useDocumentStore(state => state.currentSection);
export const useCurrentParagraph = () => useDocumentStore(state => state.currentParagraph);
export const useProjects = () => useDocumentStore(state => state.projects);
export const useSections = () => useDocumentStore(state => state.sections);
export const useIsProcessing = () => useDocumentStore(state => state.isProcessing);
export const useDocumentError = () => useDocumentStore(state => state.error);
export const useFullTranslateState = () => useDocumentStore(state => ({
  isFullTranslating: state.isFullTranslating,
  fullTranslateProgress: state.fullTranslateProgress,
  fullTranslateProjectId: state.fullTranslateProjectId,
}));

/**
 * 操作 hooks
 */
export const useDocumentActions = () =>
  useDocumentStore(state => ({
    setCurrentProject: state.setCurrentProject,
    setCurrentSection: state.setCurrentSection,
    setCurrentParagraph: state.setCurrentParagraph,
    setProjects: state.setProjects,
    setSections: state.setSections,
    setProcessing: state.setProcessing,
    setError: state.setError,
    updateProject: state.updateProject,
    updateSection: state.updateSection,
    updateParagraph: state.updateParagraph,
    updateParagraphInSection: state.updateParagraphInSection,
    updateMultipleParagraphs: state.updateMultipleParagraphs,
    goToNextSection: state.goToNextSection,
    goToPreviousSection: state.goToPreviousSection,
    goToNextParagraph: state.goToNextParagraph,
    goToPreviousParagraph: state.goToPreviousParagraph,
    reset: state.reset,
    resetCurrentProject: state.resetCurrentProject,
    // 全文翻译操作
    setFullTranslating: state.setFullTranslating,
    setFullTranslateProgress: state.setFullTranslateProgress,
    setFullTranslateProjectId: state.setFullTranslateProjectId,
    startFullTranslate: state.startFullTranslate,
    updateFullTranslateProgress: state.updateFullTranslateProgress,
    endFullTranslate: state.endFullTranslate,
  }));
