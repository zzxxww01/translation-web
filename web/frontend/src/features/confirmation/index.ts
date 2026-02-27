/**
 * 分段确认工作流 - 主导出文件
 */

// 主组件
export { ConfirmationFeature } from './index.tsx';

// 类型定义
export * from './types';

// 状态管理
export { useConfirmationStore } from './stores/confirmationStore';

// Hooks
export * from './hooks';

// API
export { confirmationApi } from './api/confirmationApi';

// 组件
export * from './components';

// 工具函数
export * from './utils';
