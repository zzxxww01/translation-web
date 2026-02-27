/**
 * useConfirmDialog hook
 * 提供便捷的确认对话框调用方式
 */

import React, { useState, useCallback, type ReactNode } from 'react';
import { ConfirmDialog, type ConfirmVariant } from './ConfirmDialog';

interface ConfirmOptions {
  title: string;
  message: string | ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
}

interface UseConfirmDialogReturn {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  ConfirmDialogComponent: () => React.ReactNode;
}

export function useConfirmDialog(): UseConfirmDialogReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const [resolveRef, setResolveRef] = useState<((value: boolean) => void) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setOptions(opts);
      setResolveRef(() => resolve);
      setIsOpen(true);
    });
  }, []);

  const handleConfirm = useCallback(() => {
    resolveRef?.(true);
    setIsOpen(false);
    setOptions(null);
    setResolveRef(null);
  }, [resolveRef]);

  const handleClose = useCallback(() => {
    resolveRef?.(false);
    setIsOpen(false);
    setOptions(null);
    setResolveRef(null);
  }, [resolveRef]);

  const ConfirmDialogComponent = useCallback(() => {
    if (!options) return null;

    return (
      <ConfirmDialog
        isOpen={isOpen}
        onClose={handleClose}
        onConfirm={handleConfirm}
        title={options.title}
        message={options.message}
        confirmText={options.confirmText}
        cancelText={options.cancelText}
        variant={options.variant}
      />
    );
  }, [isOpen, options, handleClose, handleConfirm]);

  return { confirm, ConfirmDialogComponent };
}
