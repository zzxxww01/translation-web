/**
 * 分段确认工作流 - 键盘快捷键Hook
 */

import { useEffect } from 'react';
import { useConfirmationStore } from '../stores/confirmationStore';
import { DEFAULT_SHORTCUTS } from '../types';

interface KeyboardShortcutsOptions {
  onConfirm?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  onCancel?: () => void;
  shortcuts?: Partial<typeof DEFAULT_SHORTCUTS>;
}

/**
 * 使用键盘快捷键
 */
export function useKeyboardShortcuts({
  onConfirm,
  onNext,
  onPrev,
  onCancel,
  shortcuts = {},
}: KeyboardShortcutsOptions) {
  const { isEditing } = useConfirmationStore();

  const finalShortcuts = { ...DEFAULT_SHORTCUTS, ...shortcuts };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // 如果正在编辑，不处理快捷键
      if (isEditing) return;

      // Ctrl+Enter: 确认
      if (event.ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        onConfirm?.();
      }

      // Ctrl+ArrowDown: 下一段
      if (event.ctrlKey && event.key === 'ArrowDown') {
        event.preventDefault();
        onNext?.();
      }

      // Ctrl+ArrowUp: 上一段
      if (event.ctrlKey && event.key === 'ArrowUp') {
        event.preventDefault();
        onPrev?.();
      }

      // Escape: 取消
      if (event.key === 'Escape' && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
        event.preventDefault();
        onCancel?.();
      }

      // Ctrl+1, Ctrl+2, etc: 快速选择版本
      if (event.ctrlKey && /^[1-9]$/.test(event.key)) {
        event.preventDefault();
        const versionIndex = parseInt(event.key) - 1;
        // 这里可以触发版本选择逻辑
        console.log('Select version:', versionIndex);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isEditing, onConfirm, onNext, onPrev, onCancel]);

  return finalShortcuts;
}
