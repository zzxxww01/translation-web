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

/**
 * 钳制段落下标。
 *
 * totalParagraphs 还是 0（首次加载、或后端没返回 total_paragraphs）时**不能**
 * 钳到 0：那会让 currentIndex 与面板正在显示的段落失同步，还会多打一次
 * loadParagraph(0)。此时只保证非负，等 total 到位后自然收敛。
 */
const clampParagraphIndex = (index: number, totalParagraphs: number): number => {
  const safeIndex = Number.isFinite(index) ? Math.max(0, Math.trunc(index)) : 0;
  if (totalParagraphs <= 0) return safeIndex;
  return Math.min(safeIndex, totalParagraphs - 1);
};

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
  setTotalParagraphs: (total: number) => void;
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
        // 切换项目时把段落下标复位到 0，避免沿用上一个项目的下标请求新项目导致 404
        // 注意：不能用 reset()，那会把刚设置的 projectId 一并清空
        setProjectId: (id) =>
          set((state) =>
            state.projectId === id
              ? { projectId: id }
              : { projectId: id, currentIndex: 0 }
          ),

        setWorkflowStatus: (status) => set({ workflowStatus: status }),

        setCurrentParagraph: (paragraph, versions) =>
          set({
            currentParagraph: paragraph,
            versions,
            selectedVersionId: null,
            customTranslation: '',
            isEditing: false,
          }),

        setTotalParagraphs: (total) => set({ totalParagraphs: total }),

        setSelectedVersion: (versionId) => set({ selectedVersionId: versionId }),

        setCustomTranslation: (text) => set({ customTranslation: text }),

        setIsEditing: (editing) => set({ isEditing: editing }),

        setLoading: (loading) => set({ isLoading: loading }),

        setError: (error) => set({ error }),

        goToNext: () =>
          set((state) => ({
            currentIndex: clampParagraphIndex(
              state.currentIndex + 1,
              state.totalParagraphs
            ),
          })),

        goToPrev: () =>
          set((state) => ({
            currentIndex: Math.max(state.currentIndex - 1, 0),
          })),

        // 钳制越界下标：进度条等外部调用可能传入 totalParagraphs（1-based）或负数，
        // 未钳制的坏值会让 loadParagraph 打到后端 404 并卡在错误页
        jumpTo: (index) =>
          set((state) => ({
            currentIndex: clampParagraphIndex(index, state.totalParagraphs),
          })),

        reset: () =>
          set({
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
          }),
      }),
      {
        name: 'confirmation-storage',
        // currentIndex 不再持久化：它能由 loadParagraph 成功后的 jumpTo 重建，
        // 而全局持久化会把越界坏值长期留在 localStorage，造成永久 404
        partialize: (state) => ({
          projectId: state.projectId,
        }),
        // partialize 只管写。存量用户的 localStorage 里已经有 currentIndex，
        // persist 默认 merge 仍会把那个坏下标 hydrate 回来——必须显式迁移剔除，
        // 否则本次修复对老用户在覆盖写入前完全无效。
        version: 1,
        migrate: (persisted) => {
          if (!persisted || typeof persisted !== 'object') return persisted;
          const { currentIndex: _dropped, ...rest } = persisted as Record<
            string,
            unknown
          >;
          return rest;
        },
      }
    ),
    { name: 'ConfirmationStore' }
  )
);
