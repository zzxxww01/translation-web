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
  addVersion: (content: string, type: TranslationVersion['type'], instruction?: string) => void;
  setCurrentVersion: (versionId: string) => void;
  setEditedContent: (content: string) => void;
  saveEdit: () => void;
  discardEdit: () => void;
  clear: () => void;
  setLoading: (isLoading: boolean) => void;
  getCurrentVersion: () => TranslationVersion | null;
  setSelectedModel: (model: string | undefined) => void;
}

type PostStore = PostState & PostActions;

const initialState: PostState = {
  originalText: '',
  versions: [],
  currentVersionId: null,
  isEdited: false,
  editedContent: '',
  isLoading: false,
  selectedModel: undefined,
};

export const usePostStore = create<PostStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      setOriginalText: text => set({ originalText: text }),

      addVersion: (content, type, instruction) =>
        set(state => {
          const newVersion: TranslationVersion = {
            id: `v-${Date.now()}`,
            versionNumber: state.versions.length + 1,
            content,
            type,
            instruction,
            isCurrent: true,
            createdAt: new Date(),
          };

          // 将其他版本设为非当前
          const updatedVersions = state.versions.map(v => ({
            ...v,
            isCurrent: false,
          }));

          return {
            versions: [...updatedVersions, newVersion],
            currentVersionId: newVersion.id,
            isEdited: false,
            editedContent: '',
          };
        }),

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

      saveEdit: () =>
        set(state => {
          if (!state.editedContent) return state;

          const newVersion: TranslationVersion = {
            id: `v-${Date.now()}`,
            versionNumber: state.versions.length + 1,
            content: state.editedContent,
            type: TranslationVersionType.MANUAL,
            isCurrent: true,
            createdAt: new Date(),
          };

          const updatedVersions = state.versions.map(v => ({
            ...v,
            isCurrent: false,
          }));

          return {
            versions: [...updatedVersions, newVersion],
            currentVersionId: newVersion.id,
            isEdited: false,
            editedContent: '',
          };
        }),

      discardEdit: () =>
        set({
          isEdited: false,
          editedContent: '',
        }),

      clear: () =>
        set({
          originalText: '',
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
