import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { SlackReplyVariant, ConversationMessage, MessageRole } from '../../shared/types';

interface SlackWorkspaceState {
  incomingText: string;
  incomingTranslation: string;
  incomingSuggestions: SlackReplyVariant[];
  draftText: string;
  draftVersions: SlackReplyVariant[];
  conversationMessages: ConversationMessage[];
  isHistoryCollapsed: boolean;
  setIncomingText: (value: string) => void;
  setIncomingResult: (translation: string, suggestions: SlackReplyVariant[]) => void;
  clearIncoming: () => void;
  setDraftText: (value: string) => void;
  setDraftVersions: (versions: SlackReplyVariant[]) => void;
  clearDraft: () => void;
  addMessage: (role: MessageRole, content: string) => void;
  addMessages: (role: MessageRole, contents: string[]) => void;
  removeMessage: (id: string) => void;
  updateMessage: (id: string, content: string) => void;
  clearConversation: () => void;
  toggleHistoryCollapse: () => void;
  reset: () => void;
}

const initialState = {
  incomingText: '',
  incomingTranslation: '',
  incomingSuggestions: [],
  draftText: '',
  draftVersions: [],
  conversationMessages: [],
  isHistoryCollapsed: false,
};

export const useSlackWorkspaceStore = create<SlackWorkspaceState>()(
  devtools(
    persist(
      set => ({
        ...initialState,
        setIncomingText: value =>
          set({
            incomingText: value,
            incomingTranslation: '',
            incomingSuggestions: [],
          }),
        setIncomingResult: (translation, suggestions) =>
          set({
            incomingTranslation: translation,
            incomingSuggestions: suggestions,
          }),
        clearIncoming: () =>
          set({
            incomingText: '',
            incomingTranslation: '',
            incomingSuggestions: [],
          }),
        setDraftText: value =>
          set({
            draftText: value,
            draftVersions: [],
          }),
        setDraftVersions: versions => set({ draftVersions: versions }),
        clearDraft: () =>
          set({
            draftText: '',
            draftVersions: [],
          }),
        addMessage: (role, content) =>
          set(state => ({
            conversationMessages: [
              ...state.conversationMessages,
              {
                id: crypto.randomUUID(),
                role,
                content,
                timestamp: Date.now(),
              },
            ],
          })),
        addMessages: (role, contents) =>
          set(state => ({
            conversationMessages: [
              ...state.conversationMessages,
              ...contents.map(content => ({
                id: crypto.randomUUID(),
                role,
                content,
                timestamp: Date.now(),
              })),
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
        reset: () => set(initialState),
      }),
      {
        name: 'SlackWorkspaceStore',
      }
    ),
    { name: 'SlackWorkspaceStore' }
  )
);
