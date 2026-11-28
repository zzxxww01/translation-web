import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export type CurrentTool = 'translator' | 'email' | 'timezone' | 'chat';

const TOOLS: CurrentTool[] = ['timezone', 'chat', 'translator', 'email'];

/**
 * 工具箱状态：只记住上次打开的是哪个工具。
 * 2026-11-22 去掉了「任务管理」和「Slack 回复（旧版）」；以前存下来的这两个值回到默认的时区转换。
 */
interface ToolsState {
  currentTool: CurrentTool;
  setCurrentTool: (tool: CurrentTool) => void;
}

export const useToolsStore = create<ToolsState>()(
  devtools(
    persist(
      set => ({
        currentTool: 'timezone',
        setCurrentTool: currentTool => set({ currentTool }),
      }),
      {
        name: 'ToolsStore',
        partialize: state => ({ currentTool: state.currentTool }),
        merge: (persisted, current) => {
          const saved = (persisted as Partial<ToolsState> | undefined)?.currentTool;
          return { ...current, currentTool: saved && TOOLS.includes(saved) ? saved : 'timezone' };
        },
      }
    ),
    { name: 'ToolsStore' }
  )
);
