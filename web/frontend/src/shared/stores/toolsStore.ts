import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Task } from '../types';

type CurrentTool = 'tasks' | 'translator' | 'email' | 'timezone';

/**
 * 工具箱状态
 */
interface ToolsState {
  // 当前选中的工具
  currentTool: CurrentTool;
  // 任务列表
  tasks: Task[];
  // 是否正在处理
  isProcessing: boolean;

  // Actions
  setCurrentTool: (tool: CurrentTool) => void;
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;
  toggleTask: (id: string) => void;
  setProcessing: (isProcessing: boolean) => void;
  reset: () => void;
}

const initialState = {
  currentTool: 'timezone' as CurrentTool,
  tasks: [
    { id: '1', text: '示例任务 1', completed: false },
    { id: '2', text: '示例任务 2', completed: false },
  ],
  isProcessing: false,
};

export const useToolsStore = create<ToolsState>()(
  devtools(
    persist(
      set => ({
        ...initialState,

        setCurrentTool: currentTool => set({ currentTool }),

        setTasks: tasks => set({ tasks }),

        addTask: task =>
          set(state => ({
            tasks: [...state.tasks, task],
          })),

        updateTask: (id, updates) =>
          set(state => ({
            tasks: state.tasks.map(t => (t.id === id ? { ...t, ...updates } : t)),
          })),

        deleteTask: id =>
          set(state => ({
            tasks: state.tasks.filter(t => t.id !== id),
          })),

        toggleTask: id =>
          set(state => ({
            tasks: state.tasks.map(t =>
              t.id === id ? { ...t, completed: !t.completed } : t
            ),
          })),

        setProcessing: isProcessing => set({ isProcessing }),

        reset: () => set(initialState),
      }),
      {
        name: 'ToolsStore',
        partialize: state => ({
          tasks: state.tasks,
        }),
      }
    ),
    { name: 'ToolsStore' }
  )
);
