import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { skillsApi } from '../api';
import type { Harness } from '../harness';

export function ModelPicker({ harness, value, onChange, disabled }: {
  harness: Harness;
  value: string;
  onChange: (model: string) => void;
  disabled: boolean;
}) {
  const client = useQueryClient();
  const key = ['skills', 'models', harness];
  const query = useQuery({
    queryKey: key, queryFn: () => skillsApi.models(harness),
    staleTime: 60_000, retry: false,
  });
  const refresh = useMutation({
    mutationFn: () => skillsApi.models(harness, true),
    onSuccess: data => client.setQueryData(key, data),
  });
  const fetching = query.isFetching || refresh.isPending;
  const models = query.data?.models ?? [];
  const [custom, setCustom] = useState(false);
  const unknown = Boolean(value && !models.some(model => model.id === value));
  const isCustom = custom || unknown;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="text-xs text-text-muted">
        具体模型
        <select
          aria-label="具体模型"
          className="ml-2 h-8 max-w-56 rounded-lg border border-border bg-white px-2.5 text-xs text-text-primary transition-colors hover:border-primary-200 focus:border-primary-400 focus:outline-none focus:ring-[3px] focus:ring-primary-500/12"
          value={isCustom ? '__custom__' : value}
          disabled={disabled}
          onChange={event => {
            const next = event.target.value;
            setCustom(next === '__custom__');
            onChange(next === '__custom__' ? '' : next);
          }}
        >
          <option value="">默认模型{query.data?.default_model ? ` · ${query.data.default_model}` : ''}</option>
          {models.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
          <option value="__custom__">填写模型 ID…</option>
        </select>
      </label>
      {isCustom && (
        <input
          aria-label="模型 ID" value={value} maxLength={128} disabled={disabled}
          onChange={event => onChange(event.target.value)}
          placeholder={harness === 'claude' ? '例如 opus 或完整模型 ID' : '填写完整模型 ID'}
          className="h-8 w-56 rounded-lg border border-border bg-white px-2.5 text-xs text-text-primary focus:border-primary-400 focus:outline-none focus:ring-[3px] focus:ring-primary-500/12"
        />
      )}
      {/* 清单从哪来写在按钮的悬停提示里，不再占一整行 */}
      <button type="button" disabled={disabled || fetching} onClick={() => refresh.mutate()}
        title={harness === 'codex'
          ? '来源：Codex CLI 本地缓存；刷新会重读缓存。实际可用模型取决于账号权限。'
          : query.data?.source === 'aliases'
            ? '来源：Claude 通用模型别名。'
            : `来源：服务器上的 ${harness === 'claude' ? 'Claude Code' : 'Gemini（agy）'} CLI；刷新会重新读取模型清单。清单不代表账号已登录或拥有使用权限。`}
        className="h-8 rounded-md px-2 text-xs text-text-muted transition-colors hover:bg-ink-wash hover:text-text-primary disabled:opacity-50">
        {fetching ? '读取模型…' : '刷新模型'}
      </button>
      {(query.error || refresh.error || query.data?.warning) && (
        <p role="status" className="w-full text-xs text-text-muted">
          {query.error || refresh.error ? '模型清单读取失败，仍可使用默认模型或填写模型 ID。' : query.data?.warning}
        </p>
      )}
    </div>
  );
}
