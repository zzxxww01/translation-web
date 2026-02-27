import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Conversation, Message } from '../types';

/**
 * Slack 聊天状态
 */
interface SlackState {
  // 当前选中的对话
  currentConversation: Conversation | null;
  // 对话列表
  conversations: Conversation[];
  // 当前对话的消息列表
  messages: Message[];
  // 是否正在处理
  isProcessing: boolean;

  // Actions
  setCurrentConversation: (conversation: Conversation | null) => void;
  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  deleteConversation: (id: string) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessage: (index: number, updates: Partial<Message>) => void;
  setProcessing: (isProcessing: boolean) => void;
  reset: () => void;
}

const initialState = {
  currentConversation: null,
  conversations: [],
  messages: [],
  isProcessing: false,
};

export const useSlackStore = create<SlackState>()(
  devtools(
    persist(
      set => ({
        ...initialState,

        setCurrentConversation: conversation =>
          set(state => ({
            currentConversation: conversation,
            // Only reset messages if conversation ID changes
            messages: conversation?.id !== state.currentConversation?.id 
              ? (conversation?.history || [])
              : state.messages,
          })),

        setConversations: conversations => set({ conversations }),

        addConversation: conversation =>
          set(state => ({
            conversations: [...state.conversations, conversation],
          })),

        updateConversation: (id, updates) =>
          set(state => ({
            conversations: state.conversations.map(c =>
              c.id === id ? { ...c, ...updates } : c
            ),
            currentConversation:
              state.currentConversation?.id === id
                ? { ...state.currentConversation, ...updates }
                : state.currentConversation,
          })),

        deleteConversation: id =>
          set(state => ({
            conversations: state.conversations.filter(c => c.id !== id),
            currentConversation:
              state.currentConversation?.id === id ? null : state.currentConversation,
          })),

        setMessages: messages => set({ messages }),

        addMessage: message =>
          set(state => ({
            messages: [...state.messages, message],
          })),

        updateMessage: (index, updates) =>
          set(state => ({
            messages: state.messages.map((msg, i) =>
              i === index ? { ...msg, ...updates } : msg
            ),
          })),

        setProcessing: isProcessing => set({ isProcessing }),

        reset: () => set(initialState),
      }),
      {
        name: 'SlackStore',
        partialize: state => ({
          conversations: state.conversations,
          currentConversation: state.currentConversation?.id,
        }),
      }
    ),
    { name: 'SlackStore' }
  )
);
