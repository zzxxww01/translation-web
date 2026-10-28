import * as RadioGroup from '@radix-ui/react-radio-group';
import { Gem, Sparkles, SquareTerminal, type LucideIcon } from 'lucide-react';
import { HARNESSES, type Harness } from '@/features/skills/harness';
import { rememberedModel, type AgentChoice } from '../lib/agentChoice';
import { ModelList } from './ModelList';

const LOOK: Record<Harness, { icon: LucideIcon; color: string }> = {
  codex: { icon: SquareTerminal, color: '#2b2730' },
  claude: { icon: Sparkles, color: '#c56f98' },
  antigravity: { icon: Gem, color: '#4f6d9a' },
};

/** Agent 单选卡片：图标方块 + 名字 + 一句说明 */
export function AgentCards({ options, value, onChange, disabled = false }: {
  options: Harness[];
  value: Harness;
  onChange: (harness: Harness) => void;
  disabled?: boolean;
}) {
  return (
    <RadioGroup.Root aria-label="Agent" value={value} disabled={disabled} onValueChange={next => onChange(next as Harness)}
      className="grid grid-cols-[repeat(auto-fit,minmax(132px,1fr))] gap-2">
      {options.map(id => {
        const item = HARNESSES.find(harness => harness.id === id)!;
        const { icon: Icon, color } = LOOK[id];
        return (
          <RadioGroup.Item key={id} value={id}
            className="flex min-w-0 items-center gap-2.5 rounded-xl border border-border-subtle bg-white px-3 py-2.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-200 disabled:opacity-50 data-[state=checked]:border-primary-300 data-[state=checked]:bg-primary-50 data-[state=checked]:shadow-[0_0_0_3px_rgba(163,61,112,0.08)]">
            <span aria-hidden className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white" style={{ background: color }}>
              <Icon className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-[13px] font-semibold text-text-primary">{item.label}</span>
              <span className="block truncate text-[11px] text-text-muted" title={item.note}>{item.note}</span>
            </span>
          </RadioGroup.Item>
        );
      })}
    </RadioGroup.Root>
  );
}

/** Agent 卡片 + 模型列表；换 Agent 时模型换成它上次用的 */
export function AgentChoiceFields({ options, value, onChange, disabled = false }: {
  options: Harness[];
  value: AgentChoice;
  onChange: (choice: AgentChoice) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <AgentCards options={options} value={value.harness} disabled={disabled}
        onChange={harness => onChange({ harness, model: rememberedModel(harness) })} />
      <div className="mb-1.5 mt-3.5 text-[11px] tracking-[0.12em] text-text-muted">模型</div>
      <ModelList key={value.harness} harness={value.harness} value={value.model} lastUsed={rememberedModel(value.harness)}
        disabled={disabled} onChange={model => onChange({ ...value, model })} />
    </div>
  );
}
