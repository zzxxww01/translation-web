import { Component, type ErrorInfo, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { TooltipProvider } from './components/ui/tooltip';
import { AppRouter } from './router';

// 创建 React Query 客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 分钟
    },
  },
});

class AppErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App error:', error, info);
    if (error.message.includes('Failed to fetch dynamically imported module')) {
      const reloadKey = 'translation-agent:dynamic-import-reload';
      if (sessionStorage.getItem(reloadKey) !== '1') {
        sessionStorage.setItem(reloadKey, '1');
        window.location.reload();
      }
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4">
          <div className="max-w-md text-center">
            <h2 className="mb-2 text-2xl font-bold text-foreground">出错了</h2>
            <p className="mb-4 text-muted-foreground">
              {this.state.error?.message || '应用遇到了意外错误'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AppErrorBoundary>
          <AppRouter />
          <Toaster position="top-right" richColors closeButton />
        </AppErrorBoundary>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
