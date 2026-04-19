import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { SlackReplyVariant, ConversationMessage, MessageRole } from '../../shared/types';
import type { RefinementSession } from './types';

interface SlackWorkspaceState {
  incomingText: string;
  incomingTranslation: string;
  incomingSuggestions: SlackReplyVariant[];
  draftText: string;
  draftVersions: SlackReplyVariant[];
  conversationMessages: ConversationMessage[];
  isHistoryCollapsed: boolean;
  selectedModel: string;
  incomingRefinement: RefinementSession | null;
  draftRefinement: RefinementSession | null;
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
  setSelectedModel: (model: string) => void;
  startRefinement: (contextType: 'incoming' | 'draft', originalInput: string, initialResult: string) => void;
  addRefinementVariant: (contextType: 'incoming' | 'draft', content: string) => void;
  clearRefinement: (contextType: 'incoming' | 'draft') => void;
  setRefining: (contextType: 'incoming' | 'draft', isRefining: boolean) => void;
  confirmToHistory: (contextType: 'incoming' | 'draft', variantId: string) => void;
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
  selectedModel: '',
  incomingRefinement: null,
  draftRefinement: null,
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
        setSelectedModel: model => set({ selectedModel: model }),
        startRefinement: (contextType, originalInput, initialResult) =>
          set(state => {
            const session: RefinementSession = {
              contextType,
              originalInput,
              variants: [
                {
                  id: crypto.randomUUID(),
                  content: initialResult,
                  timestamp: Date.now(),
                },
              ],
              isRefining: false,
            };
            return contextType === 'incoming'
              ? { incomingRefinement: session }
              : { draftRefinement: session };
          }),
        addRefinementVariant: (contextType, content) =>
          set(state => {
            const session = contextType === 'incoming' ? state.incomingRefinement : state.draftRefinement;
            if (!session) return state;
            const newVariant = {
              id: crypto.randomUUID(),
              content,
              timestamp: Date.now(),
            };
            const updatedSession = {
              ...session,
              variants: [...session.variants, newVariant],
              isRefining: false,
            };
            return contextType === 'incoming'
              ? { incomingRefinement: updatedSession }
              : { draftRefinement: updatedSession };
          }),
        clearRefinement: contextType =>
          set(
            contextType === 'incoming'
              ? { incomingRefinement: null }
              : { draftRefinement: null }
          ),
        setRefining: (contextType, isRefining) =>
          set(state => {
            const session = contextType === 'incoming' ? state.incomingRefinement : state.draftRefinement;
            if (!session) return state;
            const updatedSession = { ...session, isRefining };
            return contextType === 'incoming'
              ? { incomingRefinement: updatedSession }
              : { draftRefinement: updatedSession };
          }),
        confirmToHistory: (contextType, variantId) =>
          set(state => {
            const session = contextType === 'incoming' ? state.incomingRefinement : state.draftRefinement;
            if (!session) return state;
            const variant = session.variants.find(v => v.id === variantId);
            if (!variant) return state;
            const role: MessageRole = contextType === 'incoming' ? 'them' : 'me';
            return {
              conversationMessages: [
                ...state.conversationMessages,
                {
                  id: crypto.randomUUID(),
                  role,
                  content: variant.content,
                  timestamp: Date.now(),
                },
              ],
            };
          }),
        reset: () => set(initialState),
      }),
      {
        name: 'SlackWorkspaceStore',
      }
    ),
    { name: 'SlackWorkspaceStore' }
  )
);
