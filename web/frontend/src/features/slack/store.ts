import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { SlackReplyVariant } from '../../shared/types';

export interface ConversationMessage {
  id: string;
  role: 'me' | 'them';
  content: string;
  translation?: string; // 对方消息的中文翻译
  timestamp: number;
}

interface SlackWorkspaceState {
  // 当前工作区状态
  currentInput: string;
  currentVersions: SlackReplyVariant[];
  isGenerating: boolean;

  // 对话历史
  conversationMessages: ConversationMessage[];
  isHistoryCollapsed: boolean;

  // 其他
  selectedModel: string;

  // Actions
  setCurrentInput: (value: string) => void;
  setCurrentVersions: (versions: SlackReplyVariant[]) => void;
  setGenerating: (value: boolean) => void;
  clearWorkspace: () => void;

  addMessage: (role: 'me' | 'them', content: string, translation?: string) => void;
  removeMessage: (id: string) => void;
  updateMessage: (id: string, content: string) => void;
  clearConversation: () => void;
  toggleHistoryCollapse: () => void;

  setSelectedModel: (model: string) => void;
  reset: () => void;
}

const initialState = {
  currentInput: '',
  currentVersions: [],
  isGenerating: false,
  conversationMessages: [],
  isHistoryCollapsed: false,
  selectedModel: '',
};

export const useSlackWorkspaceStore = create<SlackWorkspaceState>()(
  devtools(
    persist(
      set => ({
        ...initialState,
        setCurrentInput: value => set({ currentInput: value }),
        setCurrentVersions: versions => set({ currentVersions: versions }),
        setGenerating: value => set({ isGenerating: value }),
        clearWorkspace: () =>
          set({
            currentInput: '',
            currentVersions: [],
            isGenerating: false,
          }),
        addMessage: (role, content, translation) =>
          set(state => ({
            conversationMessages: [
              ...state.conversationMessages,
              {
                id: crypto.randomUUID(),
                role,
                content,
                translation,
                timestamp: Date.now(),
              },
            ],
          })),
        removeMessage: id =>
          set(state => ({
            conversationMessages: state.conversationMessages.filter(msg => msg.id !== id),
          })),
        updateMessage: (id, content) =>
          set(state => ({
            conversationMessages: state.conversationMessages.map(msg =>
              msg.id === id ? { ...msg, content } : msg
            ),
          })),
        clearConversation: () => set({ conversationMessages: [] }),
        toggleHistoryCollapse: () =>
          set(state => ({ isHistoryCollapsed: !state.isHistoryCollapsed })),
        setSelectedModel: model => set({ selectedModel: model }),
        reset: () => set(initialState),
      }),
      {
        name: 'SlackWorkspaceStore',
        partialize: (state) => ({
          // 只持久化这些字段，conversationMessages 不持久化
          selectedModel: state.selectedModel,
          isHistoryCollapsed: state.isHistoryCollapsed,
        }),
      }
    ),
    { name: 'SlackWorkspaceStore' }
  )
);
