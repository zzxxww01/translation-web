/**
 * 确认对话框组件
 * 替代原生 confirm，提供统一的 UI 和更好的用户体验
 */

import { type ReactNode } from 'react';
import { AlertTriangle, Info, AlertCircle } from 'lucide-react';
import { Modal } from '../Modal';
import { Button } from '../Button';
import { cn } from '../../../shared/utils';

export type ConfirmVariant = 'danger' | 'warning' | 'info';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string | ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
  isLoading?: boolean;
}

const variantConfig: Record<ConfirmVariant, {
  icon: ReactNode;
  iconBg: string;
  iconColor: string;
  buttonVariant: 'danger' | 'primary';
}> = {
  danger: {
    icon: <AlertCircle className="h-6 w-6" />,
    iconBg: 'bg-error/10',
    iconColor: 'text-error',
    buttonVariant: 'danger',
  },
  warning: {
    icon: <AlertTriangle className="h-6 w-6" />,
    iconBg: 'bg-warning/10',
    iconColor: 'text-warning',
    buttonVariant: 'primary',
  },
  info: {
    icon: <Info className="h-6 w-6" />,
    iconBg: 'bg-info/10',
    iconColor: 'text-info',
    buttonVariant: 'primary',
  },
};

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = '确认',
  cancelText = '取消',
  variant = 'info',
  isLoading = false,
}: ConfirmDialogProps) {
  const config = variantConfig[variant];

  const handleConfirm = () => {
    onConfirm();
    if (!isLoading) {
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="sm"
      showCloseButton={false}
      closeOnBackdropClick={!isLoading}
      closeOnEscape={!isLoading}
    >
      <div className="text-center">
        {/* 图标 */}
        <div className={cn(
          'mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full',
          config.iconBg,
          config.iconColor
        )}>
          {config.icon}
        </div>

        {/* 标题 */}
        <h3 className="mb-2 text-lg font-semibold text-text-primary">
          {title}
        </h3>

        {/* 消息 */}
        <p className="mb-6 text-sm text-text-muted">
          {message}
        </p>

        {/* 按钮 */}
        <div className="flex justify-center gap-3">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            variant={config.buttonVariant}
            onClick={handleConfirm}
            isLoading={isLoading}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
