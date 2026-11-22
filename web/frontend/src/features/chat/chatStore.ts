import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatTurn } from './api';

export interface ChatMessage extends ChatTurn {
  id: string;
  /** 这条回复用的模型（显示名），用户消息为空 */
  model?: string;
}

interface ChatState {
  messages: ChatMessage[];
  /** 选的模型别名；默认 GPT-6.2 Sol */
  model: string;
  draft: string;
  add: (message: ChatMessage) => void;
  removeFrom: (id: string) => void;
  setModel: (model: string) => void;
  setDraft: (draft: string) => void;
  clear: () => void;
}

export const DEFAULT_CHAT_MODEL = 'gpt-6.2-sol';

/** 对话存在浏览器里：切到别的页面再回来还在；「新对话」清空 */
export const useChatStore = create<ChatState>()(
  persist(
    set => ({
      messages: [],
      model: DEFAULT_CHAT_MODEL,
      draft: '',
      add: message => set(state => ({ messages: [...state.messages, message] })),
      removeFrom: id => set(state => {
        const index = state.messages.findIndex(message => message.id === id);
        return index < 0 ? state : { messages: state.messages.slice(0, index) };
      }),
      setModel: model => set({ model }),
      setDraft: draft => set({ draft }),
      clear: () => set({ messages: [], draft: '' }),
    }),
    { name: 'momo-tools-chat' }
  )
);
