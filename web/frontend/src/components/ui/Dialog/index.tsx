import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../../../shared/utils';
import { Modal } from '../Modal';

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function Dialog({ open, onClose, children }: DialogProps) {
  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      showCloseButton={false}
      closeOnBackdropClick
      closeOnEscape
    >
      {children}
    </Modal>
  );
}

export type DialogContentProps = HTMLAttributes<HTMLDivElement>;

export function DialogContent({ className, ...props }: DialogContentProps) {
  return <div className={cn('space-y-4', className)} {...props} />;
}

export type DialogHeaderProps = HTMLAttributes<HTMLDivElement>;

export function DialogHeader({ className, ...props }: DialogHeaderProps) {
  return <div className={cn('space-y-1', className)} {...props} />;
}

export type DialogTitleProps = HTMLAttributes<HTMLHeadingElement>;

export function DialogTitle({ className, ...props }: DialogTitleProps) {
  return <h3 className={cn('text-lg font-semibold', className)} {...props} />;
}

export type DialogFooterProps = HTMLAttributes<HTMLDivElement>;

export function DialogFooter({ className, ...props }: DialogFooterProps) {
  return (
    <div
      className={cn('flex flex-wrap justify-end gap-2 pt-2', className)}
      {...props}
    />
  );
}
