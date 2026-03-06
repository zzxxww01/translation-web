import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { SlackReplyVariant } from '../../shared/types';

interface SlackWorkspaceState {
  incomingText: string;
  incomingTranslation: string;
  incomingSuggestions: SlackReplyVariant[];
  draftText: string;
  draftVersions: SlackReplyVariant[];
  setIncomingText: (value: string) => void;
  setIncomingResult: (translation: string, suggestions: SlackReplyVariant[]) => void;
  clearIncoming: () => void;
  setDraftText: (value: string) => void;
  setDraftVersions: (versions: SlackReplyVariant[]) => void;
  clearDraft: () => void;
  reset: () => void;
}

const initialState = {
  incomingText: '',
  incomingTranslation: '',
  incomingSuggestions: [],
  draftText: '',
  draftVersions: [],
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
        reset: () => set(initialState),
      }),
      {
        name: 'SlackWorkspaceStore',
      }
    ),
    { name: 'SlackWorkspaceStore' }
  )
);
