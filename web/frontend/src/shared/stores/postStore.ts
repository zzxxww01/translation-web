import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { TranslationVersion } from '../types';
import { TranslationVersionType } from '../constants';

/** 当前正在进行的网络请求类型 */
export type PostNetworkAction = 'translate' | 'optimize' | 'title';

/** 持久化时最多保留的版本数，避免长期使用后撑爆 localStorage 配额 */
const MAX_PERSISTED_VERSIONS = 20;

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
  // 当前进行中的请求类型（提升到 store，避免切走路由卸载后本地状态丢失、
  // 造成「按钮全禁用却没有任何加载指示」的假死界面）
  pendingAction: PostNetworkAction | null;
  // 当前请求的发起时间戳，用于展示已耗时
  pendingStartedAt: number | null;
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
      // 为 false 时只追加版本，不改变当前选中版本与编辑态
      // （用于把过期结果安全落库，避免清掉用户正在编辑的内容）
      makeCurrent?: boolean;
    }
  ) => string;
  setCurrentVersion: (versionId: string) => void;
  setEditedContent: (content: string) => void;
  saveEdit: () => string | null;
  discardEdit: () => void;
  clear: () => void;
  setLoading: (isLoading: boolean) => void;
  setPendingAction: (action: PostNetworkAction | null) => void;
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
  pendingAction: null,
  pendingStartedAt: null,
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
    persist(
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
          const makeCurrent = lineage?.makeCurrent !== false;
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
              isCurrent: makeCurrent,
              createdAt: new Date(),
            };

            if (!makeCurrent) {
              // 只追加，不夺取当前版本，也不动编辑态
              return {
                versions: [...currentState.versions, newVersion],
              };
            }

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
            pendingAction: null,
            pendingStartedAt: null,
          }),

        setLoading: isLoading => set({ isLoading }),

        // pendingAction 与 isLoading 始终一起写，避免二者不一致
        setPendingAction: action =>
          set({
            pendingAction: action,
            isLoading: action !== null,
            pendingStartedAt: action !== null ? Date.now() : null,
          }),

        getCurrentVersion: () => {
          const state = get();
          return state.versions.find(v => v.id === state.currentVersionId) || null;
        },

        setSelectedModel: model => set({ selectedModel: model }),
      }),
      {
        name: 'translation_agent_post_state',
        // 只持久化用户内容与偏好；isLoading / pendingAction 等瞬时状态不入库，
        // 否则刷新后会恢复成「加载中」的假死界面
        partialize: state => ({
          originalText: state.originalText,
          sourceRevision: state.sourceRevision,
          versions: state.versions.slice(-MAX_PERSISTED_VERSIONS),
          currentVersionId: state.currentVersionId,
          isEdited: state.isEdited,
          editedContent: state.editedContent,
          selectedModel: state.selectedModel,
        }),
        onRehydrateStorage: () => state => {
          if (!state) return;
          // createdAt 经 JSON 序列化后是字符串，需还原成 Date，否则时间展示会崩
          state.versions = state.versions.map(version => ({
            ...version,
            createdAt: new Date(version.createdAt),
          }));
          // 若当前版本因 slice 截断而丢失，回落到最后一个版本
          if (
            state.currentVersionId &&
            !state.versions.some(v => v.id === state.currentVersionId)
          ) {
            const fallback = state.versions[state.versions.length - 1];
            state.currentVersionId = fallback?.id ?? null;
            state.isEdited = false;
            state.editedContent = '';
            // isCurrent 标志要跟着回落，否则 store 内部两处真相不一致
            state.versions = state.versions.map(version => ({
              ...version,
              isCurrent: version.id === state.currentVersionId,
            }));
          }
          state.isLoading = false;
          state.pendingAction = null;
          state.pendingStartedAt = null;
        },
      }
    ),
    { name: 'PostStore' }
  )
);
