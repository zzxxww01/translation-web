import { useEffect, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { UNAUTHORIZED_EVENT } from '@/shared/api/client';
import { LoginPanel } from '@/features/skills/components/LoginPanel';
import { isUnauthorized, skillKeys, useSkillsAuth } from '@/features/skills/hooks';

/**
 * 全站登录门（2026-11-21）：和 Agent 页共用同一个口令登录，没登录时整页只显示口令框。
 * 真正的拦截在 nginx：momo 的 /api 先问 skill-runner 的 /api/skills/auth/check。
 * 用着用着登录过期了，任何接口的 401 都会让这里重新检查，切回口令框。
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const auth = useSkillsAuth();

  useEffect(() => {
    // 只在「以为已登录」且没在重查时重查：/me 自己的 401 也会发这个事件，不挡住会无限循环
    const onUnauthorized = () => {
      const signedIn = queryClient.getQueryState(skillKeys.me)?.status === 'success';
      if (signedIn && !queryClient.isFetching({ queryKey: skillKeys.me })) {
        void queryClient.invalidateQueries({ queryKey: skillKeys.me });
      }
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [queryClient]);

  if (auth.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
      </div>
    );
  }
  if (isUnauthorized(auth.error)) {
    return <div className="h-screen bg-background"><LoginPanel /></div>;
  }
  if (auth.isError) {
    return (
      <div className="flex h-screen items-center justify-center bg-background p-6">
        <div className="max-w-sm space-y-3 text-center text-sm text-text-secondary">
          <p>登录服务暂时连不上：{auth.error.message}</p>
          <button
            type="button"
            onClick={() => void auth.refetch()}
            className="rounded-md border border-border-subtle px-3 py-1.5 hover:bg-bg-hover"
          >
            重试
          </button>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
