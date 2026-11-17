import { useQuery } from '@tanstack/react-query';
import { fileUrl } from '@/features/skills/api';
import { useRunFiles } from '@/features/skills/hooks';
import type { RunStatus } from '@/features/skills/types';

/** skill 写的 result.json（格式见 skill_runner/skills/slack-post-translate、slack-dm-reply 的 SKILL.md）。 */
export interface PostTranslationResult {
  type: 'post_translation';
  summary?: string;
  source_text?: string;
  translation?: string;
  titles?: string[];
  permalink?: string;
}

export interface DmReplyResult {
  type: 'dm_reply';
  pending?: boolean;
  understanding?: string;
  replies?: { version: string; label?: string; english: string; chinese?: string }[];
}

export type SlackAgentResult = PostTranslationResult | DmReplyResult;

export function parseResult(raw: unknown): SlackAgentResult | null {
  if (!raw || typeof raw !== 'object') return null;
  const type = (raw as { type?: unknown }).type;
  return type === 'post_translation' || type === 'dm_reply' ? (raw as SlackAgentResult) : null;
}

/** result.json 有变化（mtime）就重新读。 */
export function useAgentResult(runId: string, status: RunStatus | null) {
  const files = useRunFiles(runId, status);
  const meta = files.data?.find(f => f.path === 'result.json');
  return useQuery({
    queryKey: ['slack-agent-result', runId, meta?.mtime],
    queryFn: async () => {
      const res = await fetch(fileUrl(runId, 'result.json'), { credentials: 'same-origin', cache: 'no-store' });
      if (!res.ok) throw new Error(`读取结果失败（${res.status}）`);
      return parseResult(await res.json());
    },
    enabled: !!meta,
    staleTime: Infinity,
  });
}
