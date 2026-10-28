import { useEffect } from 'react';
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ApiErrorWrapper, apiClient } from '@/shared/api/client';
import type { Project } from '@/shared/types';
import { substackApi, type ArticleFilter } from '@/features/substack/api';
import type { RunMeta } from '@/features/skills/types';
import { articlesApi } from './api';
import type { Workbench } from './types';

export const articleKeys = {
  library: (filter: ArticleFilter, search: string) => ['articles', 'library', filter, search] as const,
  projects: ['articles', 'projects'] as const,
  workbench: (projectId: string) => ['articles', 'workbench', projectId] as const,
  claudeRun: (runId: string) => ['articles', 'claude-run', runId] as const,
  changes: (target: string) => ['articles', 'changes', target] as const,
};

/** 有任何一路在跑就每 4 秒刷新一次；都停了就不再轮询。 */
export function workbenchBusy(data: Workbench | undefined): boolean {
  if (!data) return false;
  return data.project.status.active || data.variants.some(variant => variant.status.active);
}

export function useWorkbench(projectId: string) {
  return useQuery({
    queryKey: articleKeys.workbench(projectId),
    queryFn: () => articlesApi.workbench(projectId),
    refetchInterval: query => (workbenchBusy(query.state.data) ? 4_000 : false),
  });
}

export function useLibrary(filter: ArticleFilter, search: string) {
  return useInfiniteQuery({
    queryKey: articleKeys.library(filter, search),
    queryFn: ({ pageParam }) => substackApi.listArticles(pageParam, search, filter),
    initialPageParam: 0,
    getNextPageParam: page => page.next_offset ?? undefined,
    // 后台还在生成中文标题和摘要时，隔一会儿刷新一次
    refetchInterval: query => (query.state.data?.pages[0]?.digesting ? 15_000 : false),
  });
}

// 连续点几篇文章时不用每次都去问 Substack：两次自动检查至少隔这么久
export const AUTO_SYNC_GAP_MS = 15_000;
let lastAutoSync = 0;

/**
 * 进入文章页、刷新页面、点一篇文章、打开工作台时，都去 Substack 看一眼有没有新文章（只看最新一页，很快）。
 * key 变一次检查一次；有新文章才提示并刷新列表，失败不打扰（列表顶上的刷新按钮会报错）。
 */
export function useAutoSyncArticles(key: string) {
  const queryClient = useQueryClient();
  useEffect(() => {
    const now = Date.now();
    if (now - lastAutoSync < AUTO_SYNC_GAP_MS) return;
    lastAutoSync = now;
    substackApi.syncArticles()
      .then(result => {
        if (!result.added) return;
        toast.success(`文章库新增 ${result.added} 篇`);
        return queryClient.invalidateQueries({ queryKey: ['articles', 'library'] });
      })
      .catch(() => undefined);
  }, [key, queryClient]);
}

/** 所有主项目（孪生项目后端已经滤掉），用来列出不在文章库里的项目。 */
export function useProjects(enabled: boolean) {
  return useQuery({
    queryKey: articleKeys.projects,
    queryFn: () => apiClient.get<Project[]>('/projects'),
    enabled,
    staleTime: 30_000,
  });
}

export function useClaudeRun(runId: string | null) {
  return useQuery({
    queryKey: articleKeys.claudeRun(runId ?? ''),
    // 对话被删（404）等于没有这个任务，不是错误
    queryFn: async () => {
      try {
        return await apiClient.get<RunMeta>(`/skills/runs/${runId}`, { retry: false });
      } catch (error) {
        if (error instanceof ApiErrorWrapper && error.status === 404) return null;
        throw error;
      }
    },
    enabled: Boolean(runId),
    refetchInterval: query => {
      const run = query.state.data;
      // 在等确认时也要轮询：超时后会自动继续
      return run && (run.status === 'running' || run.status === 'waiting' || run.awaiting_reply) ? 5_000 : false;
    },
    retry: false,
  });
}
