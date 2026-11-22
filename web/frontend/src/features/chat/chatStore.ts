import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatTurn } from './api';

interface ChatState {
  /** 当前打开的会话；会话本身存在服务器上 */
  currentId: string | null;
  /** 选的模型别名；默认 GPT-6.2 Sol */
  model: string;
  /** 联网搜索：开着时模型自己决定要不要搜 */
  webSearch: boolean;
  draft: string;
  /** 旧版存在浏览器里的那段对话；第一次打开新版时导入成一个会话，然后清空 */
  messages: ChatTurn[];
  setCurrentId: (id: string | null) => void;
  setModel: (model: string) => void;
  setWebSearch: (on: boolean) => void;
  setDraft: (draft: string) => void;
  clearLegacy: () => void;
}

export const DEFAULT_CHAT_MODEL = 'gpt-6.2-sol';

export const useChatStore = create<ChatState>()(
  persist(
    set => ({
      currentId: null,
      model: DEFAULT_CHAT_MODEL,
      webSearch: true,
      draft: '',
      messages: [],
      setCurrentId: currentId => set({ currentId }),
      setModel: model => set({ model }),
      setWebSearch: webSearch => set({ webSearch }),
      setDraft: draft => set({ draft }),
      clearLegacy: () => set({ messages: [] }),
    }),
    { name: 'momo-tools-chat' }
  )
);
