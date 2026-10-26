import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { skillsApi } from '../api';
import type { Harness } from '../harness';

export function ModelPicker({ harness, value, onChange, disabled }: {
  harness: Harness;
  value: string;
  onChange: (model: string) => void;
  disabled: boolean;
}) {
  const query = useQuery({
    queryKey: ['skills', 'models', harness], queryFn: () => skillsApi.models(harness),
    staleTime: 60_000, retry: false,
  });
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
          className="ml-2 max-w-56 rounded-md border border-border bg-white px-2 py-1 text-xs text-text-primary"
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
          placeholder={harness === 'codex' ? '例如 gpt-6-astra' : '例如 opus 或完整模型 ID'}
          className="w-56 rounded-md border border-border bg-white px-2 py-1 text-xs text-text-primary"
        />
      )}
      <button type="button" disabled={disabled || query.isFetching} onClick={() => void query.refetch()}
        className="text-xs text-primary-700 disabled:opacity-50">
        {query.isFetching ? '读取模型…' : '刷新模型'}
      </button>
      {(query.error || query.data?.warning) && (
        <p role="status" className="w-full text-xs text-text-muted">
          {query.error ? '模型清单读取失败，仍可使用默认模型或填写模型 ID。' : query.data?.warning}
        </p>
      )}
    </div>
  );
}
