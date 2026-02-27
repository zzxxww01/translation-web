import { createPortal } from 'react-dom';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { cn } from '../../../shared/utils';
import { ToastContext, type Toast, type ToastContextValue, type ToastType } from './toast-context';

const toastIcons = {
  success: <CheckCircle className="h-5 w-5" />,
  error: <AlertCircle className="h-5 w-5" />,
  warning: <AlertTriangle className="h-5 w-5" />,
  info: <Info className="h-5 w-5" />,
};

const toastStyles = {
  success: 'bg-success-light border-success text-success',
  error: 'bg-error-light border-error text-error',
  warning: 'bg-warning-light border-warning text-warning',
  info: 'bg-info-light border-info text-info',
};

let toastSequence = 0;

function createToastId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `toast-${crypto.randomUUID()}`;
  }
  toastSequence += 1;
  return `toast-${toastSequence}`;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType = 'info', duration = 3000) => {
    const id = createToastId();
    const toast: Toast = { id, message, type, duration };
    setToasts(prev => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, [removeToast]);

  const value: ToastContextValue = {
    showToast: addToast,
    showSuccess: (message, duration) => addToast(message, 'success', duration),
    showError: (message, duration) => addToast(message, 'error', duration),
    showWarning: (message, duration) => addToast(message, 'warning', duration),
    showInfo: (message, duration) => addToast(message, 'info', duration),
  };

  // 监听全局 toast 事件
  useEffect(() => {
    const handleShowToast = (e: Event) => {
      const customEvent = e as CustomEvent<{ message: string; type?: ToastType; duration?: number }>;
      const { message, type, duration } = customEvent.detail;
      addToast(message, type, duration);
    };
    window.addEventListener('show-toast', handleShowToast);
    return () => window.removeEventListener('show-toast', handleShowToast);
  }, [addToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {createPortal(
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
          {toasts.map(toast => (
            <div
              key={toast.id}
              className={cn(
                'flex items-center gap-3 rounded-md border px-4 py-3 shadow-md',
                'animate-slide-up',
                toastStyles[toast.type]
              )}
            >
              <span className="flex-shrink-0">{toastIcons[toast.type]}</span>
              <span className="text-sm font-medium">{toast.message}</span>
              <button
                onClick={() => removeToast(toast.id)}
                className="ml-2 flex-shrink-0 opacity-70 hover:opacity-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}
