import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { TranslationVersion } from '../types';
import { TranslationVersionType } from '../constants';

/**
 * 帖子翻译状态
 */
interface PostState {
  // 原文
  originalText: string;
  // 原文修订号，用于识别异步返回是否已过期
  sourceRevision: number;
  // 所有翻译版本
  versions: TranslationVersion[];
  // 当前版本 ID
  currentVersionId: string | null;
  // 是否已编辑
  isEdited: boolean;
  // 编辑中的内容
  editedContent: string;
  // 是否正在加载
  isLoading: boolean;
  // 选中的模型
  selectedModel: string | undefined;
}

interface PostActions {
  // Actions
  setOriginalText: (text: string) => void;
  addVersion: (
    content: string,
    type: TranslationVersion['type'],
    instruction?: string,
    lineage?: {
      sourceRevision?: number;
      sourceText?: string;
      parentVersionId?: string;
    }
  ) => string;
  setCurrentVersion: (versionId: string) => void;
  setEditedContent: (content: string) => void;
  saveEdit: () => string | null;
  discardEdit: () => void;
  clear: () => void;
  setLoading: (isLoading: boolean) => void;
  getCurrentVersion: () => TranslationVersion | null;
  setSelectedModel: (model: string | undefined) => void;
}

type PostStore = PostState & PostActions;

const initialState: PostState = {
  originalText: '',
  sourceRevision: 0,
  versions: [],
  currentVersionId: null,
  isEdited: false,
  editedContent: '',
  isLoading: false,
  selectedModel: undefined,
};

function createVersionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `v-${crypto.randomUUID()}`;
  }
  return `v-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const usePostStore = create<PostStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      setOriginalText: text =>
        set(state => {
          if (text === state.originalText) return state;
          return {
            originalText: text,
            sourceRevision: state.sourceRevision + 1,
          };
        }),

      addVersion: (content, type, instruction, lineage) => {
        const state = get();
        const versionId = createVersionId();
        set(currentState => {
          const newVersion: TranslationVersion = {
            id: versionId,
            versionNumber: currentState.versions.length + 1,
            content,
            type,
            instruction,
            sourceRevision: lineage?.sourceRevision ?? state.sourceRevision,
            sourceText: lineage?.sourceText ?? state.originalText,
            parentVersionId: lineage?.parentVersionId,
            isCurrent: true,
            createdAt: new Date(),
          };

          // 将其他版本设为非当前
          const updatedVersions = currentState.versions.map(v => ({
            ...v,
            isCurrent: false,
          }));

          return {
            versions: [...updatedVersions, newVersion],
            currentVersionId: newVersion.id,
            isEdited: false,
            editedContent: '',
          };
        });
        return versionId;
      },

      setCurrentVersion: versionId =>
        set(state => ({
          currentVersionId: versionId,
          versions: state.versions.map(v => ({
            ...v,
            isCurrent: v.id === versionId,
          })),
          isEdited: false,
          editedContent: '',
        })),

      setEditedContent: content =>
        set(state => {
          const currentVersion = state.versions.find(v => v.id === state.currentVersionId);
          return {
            editedContent: content,
            isEdited: content !== currentVersion?.content,
          };
        }),

      saveEdit: () => {
        const state = get();
        if (!state.isEdited || !state.editedContent.trim()) return null;

        const currentVersion = state.versions.find(v => v.id === state.currentVersionId);
        const versionId = createVersionId();
        set(currentState => {
          const newVersion: TranslationVersion = {
            id: versionId,
            versionNumber: currentState.versions.length + 1,
            content: currentState.editedContent,
            type: TranslationVersionType.MANUAL,
            sourceRevision: currentVersion?.sourceRevision ?? currentState.sourceRevision,
            sourceText: currentVersion?.sourceText ?? currentState.originalText,
            parentVersionId: currentVersion?.id,
            isCurrent: true,
            createdAt: new Date(),
          };

          const updatedVersions = currentState.versions.map(v => ({
            ...v,
            isCurrent: false,
          }));

          return {
            versions: [...updatedVersions, newVersion],
            currentVersionId: newVersion.id,
            isEdited: false,
            editedContent: '',
          };
        });
        return versionId;
      },

      discardEdit: () =>
        set({
          isEdited: false,
          editedContent: '',
        }),

      clear: () =>
        set({
          originalText: '',
          sourceRevision: 0,
          versions: [],
          currentVersionId: null,
          isEdited: false,
          editedContent: '',
          isLoading: false,
        }),

      setLoading: isLoading => set({ isLoading }),

      getCurrentVersion: () => {
        const state = get();
        return state.versions.find(v => v.id === state.currentVersionId) || null;
      },

      setSelectedModel: model => set({ selectedModel: model }),
    }),
    { name: 'PostStore' }
  )
);
