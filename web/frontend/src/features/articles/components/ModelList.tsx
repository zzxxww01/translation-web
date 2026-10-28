import { useState } from 'react';
import * as RadioGroup from '@radix-ui/react-radio-group';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { skillsApi } from '@/features/skills/api';
import type { Harness } from '@/features/skills/harness';
import { cn } from '@/lib/utils';
import { FOCUS_RING } from '../lib/ui';

const DEFAULT = '__default__';
const CUSTOM = '__custom__';

/** 模型单选列表：默认（写明是哪个）/ 服务器清单 / 填写模型 ID。value 为空串 = 默认。 */
export function ModelList({ harness, value, onChange, lastUsed = '', disabled = false }: {
  harness: Harness;
  value: string;
  onChange: (model: string) => void;
  lastUsed?: string;
  disabled?: boolean;
}) {
  const client = useQueryClient();
  const key = ['skills', 'models', harness];
  const query = useQuery({ queryKey: key, queryFn: () => skillsApi.models(harness), staleTime: 60_000, retry: false });
  const refresh = useMutation({
    mutationFn: () => skillsApi.models(harness, true),
    onSuccess: data => client.setQueryData(key, data),
  });
  const models = query.data?.models ?? [];
  const [custom, setCustom] = useState(false);
  const unknown = Boolean(value) && !query.isPending && !models.some(model => model.id === value);
  const isCustom = custom || unknown;
  const selected = isCustom ? CUSTOM : value || DEFAULT;
  const fetching = query.isFetching || refresh.isPending;
  const note = query.error || refresh.error
    ? '模型清单读取失败，仍可使用默认模型或填写模型 ID'
    : query.data?.warning ?? (lastUsed ? `上次用 ${lastUsed}` : '');

  return (
    <div>
      <RadioGroup.Root aria-label="模型" value={selected} disabled={disabled}
        onValueChange={next => {
          setCustom(next === CUSTOM);
          onChange(next === CUSTOM || next === DEFAULT ? '' : next);
        }}
        className="max-h-[236px] overflow-y-auto rounded-[10px] border border-border-subtle bg-bg-secondary">
        <Option value={DEFAULT} name="默认" tag={query.data?.default_model ?? '账号默认'} />
        {models.map(model => (
          <Option key={model.id} value={model.id} name={model.label} tag={model.id === lastUsed ? '上次用' : undefined} />
        ))}
        <Option value={CUSTOM} name="填写模型 ID…" dashed />
      </RadioGroup.Root>
      {isCustom && (
        <input aria-label="模型 ID" value={value} maxLength={128} disabled={disabled} autoFocus
          onChange={event => onChange(event.target.value)}
          placeholder={harness === 'claude' ? '例如 opus 或完整模型 ID' : '填写完整模型 ID'}
          className="mt-2 w-full rounded-lg border border-border bg-bg-secondary px-2.5 py-1.5 text-[13px] text-text-primary placeholder:text-text-disabled focus:border-primary-300 focus:shadow-[0_0_0_3px_var(--color-primary-50)] focus:outline-none" />
      )}
      <p className="mt-2 flex items-center gap-2 text-[11.5px] leading-5 text-text-muted">
        <span className="min-w-0 flex-1 truncate">{note}</span>
        <button type="button" disabled={disabled || fetching} onClick={() => refresh.mutate()}
          className={cn('shrink-0 rounded-sm text-primary-700 underline-offset-[3px] hover:underline disabled:opacity-50 disabled:no-underline', FOCUS_RING)}>
          {fetching ? '读取中…' : '刷新清单'}
        </button>
      </p>
    </div>
  );
}

function Option({ value, name, tag, dashed = false }: { value: string; name: string; tag?: string; dashed?: boolean }) {
  return (
    <RadioGroup.Item value={value}
      className="group flex w-full items-center gap-2.5 border-t border-border-subtle px-3 py-2 text-left text-[13px] transition-colors first:border-t-0 hover:bg-bg-hover/60 focus-visible:bg-primary-50/70 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring disabled:opacity-50 data-[state=checked]:bg-primary-50">
      <span aria-hidden className={cn('h-[15px] w-[15px] shrink-0 rounded-full border-[1.5px] border-text-disabled bg-bg-secondary transition-[border-width] group-data-[state=checked]:border-[4.5px] group-data-[state=checked]:border-primary-500', dashed && 'border-dashed')} />
      <span className={cn('min-w-0 flex-1 truncate', dashed ? 'text-text-muted' : 'text-text-primary')}>{name}</span>
      {tag && <span className="shrink-0 text-[11px] text-text-muted group-data-[state=checked]:text-primary-700">{tag}</span>}
    </RadioGroup.Item>
  );
}
