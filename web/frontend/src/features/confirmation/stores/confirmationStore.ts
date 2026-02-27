/**
 * 分段确认工作流 - Zustand状态管理
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  Paragraph,
  ParagraphVersion,
  WorkflowStatus,
} from '../types';

interface ConfirmationState {
  // 项目状态
  projectId: string | null;
  workflowStatus: WorkflowStatus;

  // 段落状态
  currentIndex: number;
  totalParagraphs: number;
  currentParagraph: Paragraph | null;
  versions: ParagraphVersion[];
  selectedVersionId: string | null;

  // 编辑状态
  customTranslation: string;
  isEditing: boolean;

  // 加载状态
  isLoading: boolean;
  error: string | null;

  // 操作方法
  setProjectId: (id: string) => void;
  setWorkflowStatus: (status: WorkflowStatus) => void;
  setCurrentParagraph: (
    paragraph: Paragraph,
    versions: ParagraphVersion[]
  ) => void;
  setSelectedVersion: (versionId: string) => void;
  setCustomTranslation: (text: string) => void;
  setIsEditing: (editing: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  goToNext: () => void;
  goToPrev: () => void;
  jumpTo: (index: number) => void;
  reset: () => void;
}

export const useConfirmationStore = create<ConfirmationState>()(
  devtools(
    persist(
      (set) => ({
        // 初始状态
        projectId: null,
        workflowStatus: 'loading',
        currentIndex: 0,
        totalParagraphs: 0,
        currentParagraph: null,
        versions: [],
        selectedVersionId: null,
        customTranslation: '',
        isEditing: false,
        isLoading: false,
        error: null,

        // 操作方法
        setProjectId: (id) => set({ projectId: id }),

        setWorkflowStatus: (status) => set({ workflowStatus: status }),

        setCurrentParagraph: (paragraph, versions) =>
          set({
            currentParagraph: paragraph,
            versions,
            selectedVersionId: null,
            customTranslation: '',
            isEditing: false,
          }),

        setSelectedVersion: (versionId) => set({ selectedVersionId: versionId }),

        setCustomTranslation: (text) => set({ customTranslation: text }),

        setIsEditing: (editing) => set({ isEditing: editing }),

        setLoading: (loading) => set({ isLoading: loading }),

        setError: (error) => set({ error }),

        goToNext: () =>
          set((state) => ({
            currentIndex: Math.min(state.currentIndex + 1, state.totalParagraphs - 1),
          })),

        goToPrev: () =>
          set((state) => ({
            currentIndex: Math.max(state.currentIndex - 1, 0),
          })),

        jumpTo: (index) => set({ currentIndex: index }),

        reset: () =>
          set({
            projectId: null,
            workflowStatus: 'loading',
            currentIndex: 0,
            currentParagraph: null,
            versions: [],
            selectedVersionId: null,
            customTranslation: '',
            isEditing: false,
            isLoading: false,
            error: null,
          }),
      }),
      {
        name: 'confirmation-storage',
        partialize: (state) => ({
          projectId: state.projectId,
          currentIndex: state.currentIndex,
        }),
      }
    ),
    { name: 'ConfirmationStore' }
  )
);
