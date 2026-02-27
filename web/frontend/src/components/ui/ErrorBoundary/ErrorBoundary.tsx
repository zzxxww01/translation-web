/**
 * 错误边界组件
 * 捕获 React 渲染错误，防止整个应用崩溃
 */

import { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // 记录错误信息
    console.error('ErrorBoundary caught an error:', error);
    console.error('Error info:', errorInfo);

    this.setState({ errorInfo });

    // 调用外部错误处理回调
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleGoHome = (): void => {
    window.location.href = '/';
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // 如果提供了自定义 fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认错误 UI
      return (
        <div className="flex h-full min-h-[400px] items-center justify-center bg-bg-primary p-8">
          <div className="max-w-md text-center">
            {/* 错误图标 */}
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-error/10">
              <AlertTriangle className="h-8 w-8 text-error" />
            </div>

            {/* 标题 */}
            <h2 className="mb-2 text-xl font-bold text-text-primary">出错了</h2>
            <p className="mb-6 text-text-muted">
              抱歉，页面发生了一些问题。请尝试刷新页面或返回首页。
            </p>

            {/* 错误详情（开发环境显示） */}
            {import.meta.env.DEV && this.state.error && (
              <div className="mb-6 rounded-lg bg-bg-tertiary p-4 text-left">
                <p className="mb-2 text-sm font-medium text-error">
                  {this.state.error.name}: {this.state.error.message}
                </p>
                {this.state.errorInfo?.componentStack && (
                  <pre className="max-h-32 overflow-auto text-xs text-text-muted">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex justify-center gap-4">
              <button
                onClick={this.handleRetry}
                className="inline-flex items-center gap-2 rounded-xl bg-primary-500 px-4 py-2 font-medium text-white transition-all hover:bg-primary-600"
              >
                <RefreshCw className="h-4 w-4" />
                重试
              </button>
              <button
                onClick={this.handleGoHome}
                className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2 font-medium text-text-primary transition-all hover:bg-bg-tertiary"
              >
                <Home className="h-4 w-4" />
                返回首页
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
