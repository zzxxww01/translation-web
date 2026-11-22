import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient, ApiErrorWrapper } from '@/shared/api/client';
import { postSnapshot, type PostSnapshot, type PostStoreHook } from '@/shared/stores/postStore';

/** 翻译记录列表里的一行（后端 summarize） */
export interface DraftSummary {
  id: string;
  source: 'manual' | 'slack';
  status: 'draft' | 'done';
  auto: boolean;
  seen: boolean;
  title: string;
  preview: string;
  source_preview: string;
  versions: number;
  images: string[];
  image_count: number;
  slack: { channel_id: string; thread_ts: string; channel_name?: string; title?: string } | null;
  created_at: number;
  updated_at: number;
}

export interface DraftImage {
  id: string;
  name: string;
}

export interface DraftExtraction {
  has_post: boolean;
  note: string;
  message_ts: string[];
  candidates: { label: string; source_text: string; message_ts: string[]; image_ids: string[] }[];
  instruction: string;
  extracted_at: number;
  latest_ts: string;
}

export interface DraftDoc {
  id: string;
  source: 'manual' | 'slack';
  status: 'draft' | 'done';
  auto: boolean;
  seen: boolean;
  rev: number;
  state: PostSnapshot;
  images: DraftImage[];
  slack?: { channel_id: string; thread_ts: string; channel_name: string; title: string; permalink: string; latest_ts: string } | null;
  extraction?: DraftExtraction;
  created_at: number;
  updated_at: number;
}

export interface DraftExtra {
  images?: DraftImage[];
  status?: 'draft' | 'done';
  seen?: boolean;
}

export const draftsApi = {
  list: (q = '', source = '') =>
    apiClient.get<{ items: DraftSummary[] }>('/post-drafts', { params: { q, source }, retry: false }),
  get: (id: string) => apiClient.get<DraftDoc>(`/post-drafts/${id}`, { retry: false }),
  create: (body: { state: PostSnapshot } & DraftExtra) => apiClient.post<DraftDoc>('/post-drafts', body, { retry: false }),
  save: (id: string, body: { state: PostSnapshot; rev: number | null } & DraftExtra) =>
    apiClient.put<DraftDoc>(`/post-drafts/${id}`, body, { retry: false }),
  slack: (channelId: string, threadTs: string) =>
    apiClient.get<{ draft: DraftDoc | null }>(`/post-drafts/slack/${channelId}/${threadTs}`, { retry: false }),
  runSlack: (channelId: string, threadTs: string, instruction?: string) =>
    apiClient.post<DraftDoc>(`/post-drafts/slack/${channelId}/${threadTs}/run`, { instruction: instruction || null }, {
      retry: false,
      timeout: 300_000,
    }),
  imagesZipUrl: (id: string) => `/api/post-drafts/${id}/images.zip`,
};

export const draftKeys = {
  list: (q: string) => ['post-drafts', 'list', q] as const,
  slack: (channelId: string, threadTs: string) => ['post-drafts', 'slack', channelId, threadTs] as const,
};

export function useDraftList(q: string) {
  return useQuery({
    queryKey: draftKeys.list(q),
    queryFn: () => draftsApi.list(q),
    select: data => data.items,
    staleTime: 10_000,
  });
}

const SAVE_DELAY_MS = 800;
const SNAPSHOT_FIELDS = [
  'originalText', 'sourceRevision', 'versions', 'currentVersionId', 'versionMetadata',
  'generatedTitles', 'selectedTitle', 'titleContentIdentity',
] as const;

/**
 * 把工作区 store 自动存到服务器翻译稿：内容变了 0.8 秒后存一次。
 * - 帖子翻译页（manual）：出过第一版译文才建稿；
 * - Slack：稿子已经由后端流程建好，这里只管保存修改。
 * 存的时候别处改过（409）：载入服务器上的最新版。
 */
export function useDraftSync(
  useStore: PostStoreHook,
  { enabled = true, extra }: { enabled?: boolean; extra?: () => DraftExtra } = {}
) {
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const lastSaved = useRef<string>('');
  const timer = useRef<number | null>(null);
  const extraRef = useRef(extra);
  useEffect(() => {
    extraRef.current = extra;
  });

  const payload = useCallback(() => {
    const state = useStore.getState();
    return { state: postSnapshot(state), ...(extraRef.current?.() ?? {}) };
  }, [useStore]);

  const flush = useCallback(async () => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = null;
    const state = useStore.getState();
    const body = payload();
    const key = JSON.stringify(body);
    if (key === lastSaved.current) return;
    if (!state.draftId && body.state.versions.length === 0) return;
    if (state.pendingAction) return; // 请求结束后会再触发一次
    setSaving(true);
    try {
      const doc = state.draftId
        ? await draftsApi.save(state.draftId, { ...body, rev: state.draftRev })
        : await draftsApi.create(body);
      lastSaved.current = key;
      useStore.getState().setDraft(doc.id, doc.rev);
      setSavedAt(Date.now());
      void queryClient.invalidateQueries({ queryKey: ['post-drafts'] });
    } catch (error) {
      if (error instanceof ApiErrorWrapper && error.status === 409 && state.draftId) {
        const latest = await draftsApi.get(state.draftId);
        useStore.getState().loadSnapshot(latest.state, latest.id, latest.rev);
        lastSaved.current = JSON.stringify({ state: postSnapshot(useStore.getState()), ...(extraRef.current?.() ?? {}) });
        toast.info('这份翻译稿在别处改过，已载入最新内容');
      } else {
        toast.error(error instanceof Error ? `翻译稿没存上：${error.message}` : '翻译稿没存上');
      }
    } finally {
      setSaving(false);
    }
  }, [payload, queryClient, useStore]);

  const schedule = useCallback(() => {
    if (!enabled) return;
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void flush(), SAVE_DELAY_MS);
  }, [enabled, flush]);

  /** 刚从服务器载入：以它为基准，不要马上又存回去 */
  const markLoaded = useCallback(() => {
    lastSaved.current = JSON.stringify(payload());
  }, [payload]);

  useEffect(() => {
    if (!enabled) return;
    const unsubscribe = useStore.subscribe((state, prev) => {
      if (state.pendingAction !== prev.pendingAction && !state.pendingAction) {
        schedule();
        return;
      }
      if (SNAPSHOT_FIELDS.some(field => state[field] !== prev[field])) schedule();
    });
    return () => {
      unsubscribe();
      if (timer.current) {
        window.clearTimeout(timer.current);
        void flush();
      }
    };
  }, [enabled, flush, schedule, useStore]);

  return { saving, savedAt, flush, schedule, markLoaded };
}
