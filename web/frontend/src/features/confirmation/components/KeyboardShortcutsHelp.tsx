/**
 * 快捷键提示组件
 * 显示所有可用的键盘快捷键
 */

import { useState } from 'react';
import { Keyboard, X } from 'lucide-react';
import { cn } from '../../../shared/utils';
import { DEFAULT_SHORTCUTS } from '../types';

interface KeyboardShortcutsHelpProps {
  shortcuts?: Partial<typeof DEFAULT_SHORTCUTS>;
  className?: string;
}

export function KeyboardShortcutsHelp({
  shortcuts = DEFAULT_SHORTCUTS,
  className,
}: KeyboardShortcutsHelpProps) {
  const [isOpen, setIsOpen] = useState(false);

  const shortcutItems = [
    { key: 'Ctrl+Enter', description: '确认当前译文', action: shortcuts.confirm },
    { key: 'Ctrl+↓', description: '跳转到下一段', action: shortcuts.next },
    { key: 'Ctrl+↑', description: '跳转到上一段', action: shortcuts.prev },
    { key: 'Esc', description: '取消编辑', action: shortcuts.cancel },
    { key: 'Ctrl+1-9', description: '快速选择版本', action: '快速选择' },
  ];

  return (
    <>
      {/* 触发按钮 */}
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          'fixed bottom-4 right-4 z-40',
          'p-3 rounded-full bg-primary/10',
          'hover:bg-primary/20 transition-colors',
          'text-primary',
          'shadow-lg',
          className
        )}
        title="查看快捷键"
      >
        <Keyboard className="h-5 w-5" />
      </button>

      {/* 快捷键面板 */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-card rounded-2xl shadow-2xl max-w-md w-full p-6">
            {/* 标题栏 */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Keyboard className="h-5 w-5 text-primary" />
                </div>
                <h3 className="text-lg font-semibold text-text-primary">键盘快捷键</h3>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-lg hover:bg-bg-tertiary transition-colors"
              >
                <X className="h-5 w-5 text-text-secondary" />
              </button>
            </div>

            {/* 快捷键列表 */}
            <div className="space-y-3">
              {shortcutItems.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary"
                >
                  <div className="flex items-center gap-3">
                    <kbd className="px-2 py-1 text-xs font-mono font-medium text-text-primary bg-bg-secondary border border-border rounded">
                      {item.key}
                    </kbd>
                    <span className="text-sm text-text-secondary">{item.description}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* 提示 */}
            <div className="mt-6 p-4 rounded-lg bg-info/10">
              <p className="text-sm text-info">
                💡 使用快捷键可以大幅提高翻译确认效率
              </p>
            </div>

            {/* 关闭按钮 */}
            <button
              onClick={() => setIsOpen(false)}
              className="w-full mt-6 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/600 transition-colors font-medium"
            >
              知道了
            </button>
          </div>
        </div>
      )}
    </>
  );
}
