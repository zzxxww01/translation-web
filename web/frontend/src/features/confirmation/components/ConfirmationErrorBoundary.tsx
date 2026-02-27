/**
 * 分段确认工作流 - 错误边界组件
 * 捕获组件树中的错误并提供友好的错误UI
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { cn } from '../../../shared/utils';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ConfirmationErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Confirmation workflow error:', error, errorInfo);

    // 调用错误回调
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // 使用自定义fallback或默认错误UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex h-screen items-center justify-center bg-background p-4">
          <div className="max-w-md w-full text-center">
            <div className="mb-6 inline-flex p-4 rounded-full bg-error/10">
              <AlertTriangle className="h-12 w-12 text-error" />
            </div>

            <h2 className="text-2xl font-bold text-text-primary mb-2">
              出错了
            </h2>

            <p className="text-text-secondary mb-6">
              工作流遇到了一个意外错误。您可以尝试刷新页面或重新开始。
            </p>

            {this.state.error && (
              <details className="mb-6 text-left">
                <summary className="cursor-pointer text-sm font-medium text-text-muted hover:text-text-secondary mb-2">
                  错误详情
                </summary>
                <div className="mt-2 p-4 rounded-lg bg-bg-tertiary">
                  <code className="text-xs text-text-secondary break-all">
                    {this.state.error.message}
                  </code>
                </div>
              </details>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className={cn(
                  'inline-flex items-center gap-2 px-6 py-2',
                  'bg-primary text-white rounded-lg',
                  'hover:bg-primary/600 transition-colors',
                  'font-medium'
                )}
              >
                <RefreshCw className="h-4 w-4" />
                重试
              </button>
              <button
                onClick={() => window.location.reload()}
                className={cn(
                  'inline-flex items-center gap-2 px-6 py-2',
                  'border border-border text-text-primary rounded-lg',
                  'hover:bg-bg-tertiary transition-colors',
                  'font-medium'
                )}
              >
                刷新页面
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
