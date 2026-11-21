import { create, type StoreApi, type UseBoundStore } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import type { TranslationVersion } from '../types';
import { TranslationVersionType } from '../constants';

export interface PostVersionMetadata {
  name: string;
  pinned: boolean;
  modelAlias?: string;
  modelUsed?: string;
  providerUsed?: string;
  fallbackUsed?: boolean;
}

export type PostTaskKind = 'translate' | 'optimize' | 'title' | 'hashtags';
export type PostNetworkAction = PostTaskKind;
export type PostTaskProgressState =
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface PostActiveTask {
  kind: PostTaskKind;
  label: string;
  startedAt: number;
  progressState: PostTaskProgressState;
  message?: string;
}

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
  // 最近一次网络动作，用于页面和全局任务条显示及过期保护
  pendingAction: PostNetworkAction | null;
  pendingStartedAt: number | null;
  // 选中的模型
  selectedModel: string | undefined;
  // 版本的展示信息
  versionMetadata: Record<string, PostVersionMetadata>;
  // 发布标题
  generatedTitles: string[];
  selectedTitle: string;
  titleContentIdentity: string;
  // 发布标签（不混入译文正文）
  hashtags: string[];
  // 自定义优化要求
  customInstruction: string;
  // 当前或刚结束的长请求，供页面和全局任务条共享
  activeTask: PostActiveTask | null;
  cancelActiveTask: (() => void) | null;
  // 服务器上的翻译稿（翻译记录）：还没出过译文时为空
  draftId: string | null;
  draftRev: number | null;
}

/** 存到服务器翻译稿里的那部分（和后端 state 字段同构） */
export type PostSnapshot = Pick<
  PostState,
  | 'originalText'
  | 'sourceRevision'
  | 'versions'
  | 'currentVersionId'
  | 'versionMetadata'
  | 'generatedTitles'
  | 'selectedTitle'
  | 'titleContentIdentity'
>;

export function postSnapshot(state: PostState): PostSnapshot {
  return {
    originalText: state.originalText,
    sourceRevision: state.sourceRevision,
    versions: state.versions,
    currentVersionId: state.currentVersionId,
    versionMetadata: state.versionMetadata,
    generatedTitles: state.generatedTitles,
    selectedTitle: state.selectedTitle,
    titleContentIdentity: state.titleContentIdentity,
  };
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
      modelAlias?: string;
      modelUsed?: string;
      providerUsed?: string;
      fallbackUsed?: boolean;
      makeCurrent?: boolean;
    }
  ) => string;
  setCurrentVersion: (versionId: string) => void;
  renameVersion: (versionId: string, name: string) => void;
  toggleVersionPinned: (versionId: string) => void;
  deleteVersion: (versionId: string) => void;
  setEditedContent: (content: string) => void;
  saveEdit: () => string | null;
  discardEdit: () => void;
  clear: () => void;
  setLoading: (isLoading: boolean) => void;
  setPendingAction: (action: PostNetworkAction | null, startedAt?: number) => void;
  getCurrentVersion: () => TranslationVersion | null;
  setSelectedModel: (model: string | undefined) => void;
  setGeneratedTitles: (titles: string[], contentIdentity: string) => void;
  setSelectedTitle: (title: string) => void;
  setHashtags: (hashtags: string[]) => void;
  addHashtag: (hashtag: string) => void;
  updateHashtag: (index: number, hashtag: string) => void;
  removeHashtag: (index: number) => void;
  moveHashtag: (index: number, direction: -1 | 1) => void;
  setCustomInstruction: (instruction: string) => void;
  startTask: (
    task: Omit<PostActiveTask, 'startedAt' | 'progressState'>,
    cancel: () => void
  ) => void;
  finishTask: (
    progressState: Exclude<PostTaskProgressState, 'running'>,
    message?: string
  ) => void;
  clearTask: () => void;
  setDraft: (draftId: string | null, draftRev: number | null) => void;
  /** 打开一份翻译稿：整份换掉当前内容 */
  loadSnapshot: (snapshot: Partial<PostSnapshot>, draftId: string | null, draftRev: number | null) => void;
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
  versionMetadata: {},
  generatedTitles: [],
  selectedTitle: '',
  titleContentIdentity: '',
  hashtags: [],
  customInstruction: '',
  activeTask: null,
  cancelActiveTask: null,
  draftId: null,
  draftRev: null,
};

function createVersionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `v-${crypto.randomUUID()}`;
  }
  return `v-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const MAX_PERSISTED_VERSIONS = 20;

/**
 * 帖子翻译工作区的全部逻辑（版本、编辑、标题……）。帖子翻译页用持久化在浏览器里的那一份（usePostStore），
 * Slack 翻译模式每篇帖子另建一份不持久化的（createPostStore），两边行为完全一致。
 */
function postStoreCreator(
  set: StoreApi<PostStore>['setState'],
  get: StoreApi<PostStore>['getState']
): PostStore {
  return {
        ...initialState,

        setOriginalText: text =>
          set(state => {
            if (text === state.originalText) return state;
            return {
              originalText: text,
              sourceRevision: state.sourceRevision + 1,
              generatedTitles: [],
              selectedTitle: '',
              titleContentIdentity: '',
              hashtags: [],
            };
          }),

        addVersion: (content, type, instruction, lineage) => {
          const state = get();
          const versionId = createVersionId();
          const makeCurrent = lineage?.makeCurrent !== false;
          set(currentState => {
            const newVersion: TranslationVersion = {
              id: versionId,
              versionNumber:
                Math.max(0, ...currentState.versions.map(version => version.versionNumber)) + 1,
              content,
              type,
              instruction,
              sourceRevision: lineage?.sourceRevision ?? state.sourceRevision,
              sourceText: lineage?.sourceText ?? state.originalText,
              parentVersionId: lineage?.parentVersionId,
              isCurrent: makeCurrent,
              createdAt: new Date(),
            };

            const typeName =
              type === TranslationVersionType.TRANSLATION
                ? '初始翻译'
                : type === TranslationVersionType.OPTIMIZATION
                  ? '优化版本'
                  : '手工编辑';

            const versions = makeCurrent
              ? [
                  ...currentState.versions.map(v => ({ ...v, isCurrent: false })),
                  newVersion,
                ]
              : [...currentState.versions, newVersion];

            return {
              versions,
              versionMetadata: {
                ...currentState.versionMetadata,
                [versionId]: {
                  name: `${typeName} v${newVersion.versionNumber}`,
                  pinned: false,
                  modelAlias: lineage?.modelAlias,
                  modelUsed: lineage?.modelUsed,
                  providerUsed: lineage?.providerUsed,
                  fallbackUsed: lineage?.fallbackUsed,
                },
              },
              ...(makeCurrent
                ? {
                    currentVersionId: newVersion.id,
                    isEdited: false,
                    editedContent: '',
                  }
                : {}),
            };
          });
          return versionId;
        },

        setCurrentVersion: versionId =>
          set(state => {
            if (!state.versions.some(version => version.id === versionId)) return state;
            return {
              currentVersionId: versionId,
              versions: state.versions.map(v => ({
                ...v,
                isCurrent: v.id === versionId,
              })),
              isEdited: false,
              editedContent: '',
            };
          }),

        renameVersion: (versionId, name) =>
          set(state => {
            const metadata = state.versionMetadata[versionId];
            const normalizedName = name.trim();
            if (!metadata || !normalizedName) return state;
            return {
              versionMetadata: {
                ...state.versionMetadata,
                [versionId]: { ...metadata, name: normalizedName },
              },
            };
          }),

        toggleVersionPinned: versionId =>
          set(state => {
            const metadata = state.versionMetadata[versionId];
            if (!metadata) return state;
            return {
              versionMetadata: {
                ...state.versionMetadata,
                [versionId]: { ...metadata, pinned: !metadata.pinned },
              },
            };
          }),

        deleteVersion: versionId =>
          set(state => {
            if (!state.versions.some(version => version.id === versionId)) return state;
            const versions = state.versions.filter(version => version.id !== versionId);
            const nextCurrentId =
              state.currentVersionId === versionId
                ? (versions.at(-1)?.id ?? null)
                : state.currentVersionId;
            const versionMetadata = { ...state.versionMetadata };
            delete versionMetadata[versionId];
            return {
              versions: versions.map(version => ({
                ...version,
                isCurrent: version.id === nextCurrentId,
              })),
              versionMetadata,
              currentVersionId: nextCurrentId,
              isEdited: false,
              editedContent: '',
            };
          }),

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
          return get().addVersion(
            state.editedContent,
            TranslationVersionType.MANUAL,
            undefined,
            {
              sourceRevision: currentVersion?.sourceRevision ?? state.sourceRevision,
              sourceText: currentVersion?.sourceText ?? state.originalText,
              parentVersionId: currentVersion?.id,
              modelAlias: state.versionMetadata[currentVersion?.id ?? '']?.modelAlias,
            }
          );
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
            versionMetadata: {},
            currentVersionId: null,
            isEdited: false,
            editedContent: '',
            isLoading: false,
            pendingAction: null,
            pendingStartedAt: null,
            generatedTitles: [],
            selectedTitle: '',
            titleContentIdentity: '',
            hashtags: [],
            customInstruction: '',
            activeTask: null,
            cancelActiveTask: null,
            draftId: null,
            draftRev: null,
          }),

        setLoading: isLoading => set({ isLoading }),

        setPendingAction: (pendingAction, startedAt = Date.now()) =>
          set({
            pendingAction,
            pendingStartedAt: pendingAction ? startedAt : null,
            isLoading: Boolean(pendingAction),
          }),

        getCurrentVersion: () => {
          const state = get();
          return state.versions.find(v => v.id === state.currentVersionId) || null;
        },

        setSelectedModel: model => set({ selectedModel: model }),

        setGeneratedTitles: (titles, contentIdentity) =>
          set(state => {
            const normalizedTitles = Array.from(
              new Set(titles.map(title => title.trim()).filter(Boolean))
            );
            return {
              generatedTitles: normalizedTitles,
              selectedTitle: normalizedTitles.includes(state.selectedTitle)
                ? state.selectedTitle
                : (normalizedTitles[0] ?? ''),
              titleContentIdentity: contentIdentity,
            };
          }),

        setSelectedTitle: title => set({ selectedTitle: title }),

        setHashtags: hashtags =>
          set({
            hashtags: Array.from(new Set(hashtags.map(tag => tag.trim()).filter(Boolean))),
          }),

        addHashtag: hashtag =>
          set(state => {
            const normalized = hashtag.trim();
            if (!normalized || state.hashtags.includes(normalized)) return state;
            return { hashtags: [...state.hashtags, normalized] };
          }),

        updateHashtag: (index, hashtag) =>
          set(state => {
            const normalized = hashtag.trim();
            if (
              !normalized ||
              index < 0 ||
              index >= state.hashtags.length ||
              state.hashtags.some((tag, tagIndex) => tagIndex !== index && tag === normalized)
            ) {
              return state;
            }
            return {
              hashtags: state.hashtags.map((tag, tagIndex) =>
                tagIndex === index ? normalized : tag
              ),
            };
          }),

        removeHashtag: index =>
          set(state => ({
            hashtags: state.hashtags.filter((_, tagIndex) => tagIndex !== index),
          })),

        moveHashtag: (index, direction) =>
          set(state => {
            const targetIndex = index + direction;
            if (
              index < 0 ||
              targetIndex < 0 ||
              index >= state.hashtags.length ||
              targetIndex >= state.hashtags.length
            ) {
              return state;
            }
            const hashtags = [...state.hashtags];
            [hashtags[index], hashtags[targetIndex]] = [
              hashtags[targetIndex],
              hashtags[index],
            ];
            return { hashtags };
          }),

        setCustomInstruction: customInstruction => set({ customInstruction }),

        startTask: (task, cancel) =>
          set({
            activeTask: {
              ...task,
              startedAt: Date.now(),
              progressState: 'running',
            },
            cancelActiveTask: cancel,
          }),

        finishTask: (progressState, message) =>
          set(state => ({
            activeTask: state.activeTask
              ? { ...state.activeTask, progressState, message }
              : null,
            cancelActiveTask: null,
          })),

        clearTask: () => set({ activeTask: null, cancelActiveTask: null }),

        setDraft: (draftId, draftRev) => set({ draftId, draftRev }),

        loadSnapshot: (snapshot, draftId, draftRev) =>
          set({
            ...initialState,
            ...snapshot,
            versions: (snapshot.versions ?? []).map(version => ({
              ...version,
              createdAt: new Date(version.createdAt),
            })),
            draftId,
            draftRev,
          }),
  };
}

export type PostStoreHook = UseBoundStore<StoreApi<PostStore>>;

/** Slack 翻译模式用：每篇帖子一份，不写浏览器存储（内容存在服务器的翻译稿里） */
export function createPostStore(): PostStoreHook {
  return create<PostStore>()((set, get) => postStoreCreator(set, get));
}

export const usePostStore: PostStoreHook = create<PostStore>()(
  devtools(
    persist(
      (set, get) => postStoreCreator(set, get),
      {
        name: 'translation-post-workspace',
        version: 1,
        storage: createJSONStorage(() => localStorage),
        partialize: state => ({
          originalText: state.originalText,
          sourceRevision: state.sourceRevision,
          versions: state.versions.slice(-MAX_PERSISTED_VERSIONS),
          currentVersionId: state.currentVersionId,
          isEdited: state.isEdited,
          editedContent: state.editedContent,
          selectedModel: state.selectedModel,
          versionMetadata: state.versionMetadata,
          generatedTitles: state.generatedTitles,
          selectedTitle: state.selectedTitle,
          titleContentIdentity: state.titleContentIdentity,
          hashtags: state.hashtags,
          customInstruction: state.customInstruction,
          draftId: state.draftId,
          draftRev: state.draftRev,
        }),
        merge: (persisted, current) => {
          const saved = persisted as Partial<PostState>;
          return {
            ...current,
            ...saved,
            isLoading: false,
            activeTask: null,
            cancelActiveTask: null,
            versions: (saved.versions ?? current.versions)
              .slice(-MAX_PERSISTED_VERSIONS)
              .map(version => ({
              ...version,
              createdAt: new Date(version.createdAt),
              })),
            pendingAction: null,
            pendingStartedAt: null,
          };
        },
      }
    ),
    { name: 'PostStore' }
  )
);
