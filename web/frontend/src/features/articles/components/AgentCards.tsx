import * as RadioGroup from '@radix-ui/react-radio-group';
import { HARNESSES, type Harness } from '@/features/skills/harness';
import { cn } from '@/lib/utils';
import { rememberedModel, type AgentChoice } from '../lib/agentChoice';
import { FOCUS_RING } from '../lib/ui';
import { ModelList } from './ModelList';

/**
 * 首字母方块头像的底色（设计文档 6.5）。Codex 和 Claude 都是 C，靠一点低饱和的底色区分；
 * 全用主题里的浅色和对应的深色字，不用品牌色，和纸面一样安静。梅红留给「选中」。
 */
const AVATAR: Record<Harness, string> = {
  codex: 'bg-bg-inset text-text-primary',
  claude: 'bg-warning-light text-warning-text',
  antigravity: 'bg-info-light text-info',
};

/** Agent 单选卡片：首字母方块头像 + 名字 + 一句说明。窄处（弹框）一张一行，宽处（导入页）三张并排。 */
export function AgentCards({ options, value, onChange, disabled = false }: {
  options: Harness[];
  value: Harness;
  onChange: (harness: Harness) => void;
  disabled?: boolean;
}) {
  return (
    <div className="@container">
      <RadioGroup.Root aria-label="Agent" value={value} disabled={disabled} onValueChange={next => onChange(next as Harness)}
        className="grid grid-cols-1 gap-1.5 @min-[34rem]:grid-cols-3 @min-[34rem]:gap-2">
        {options.map(id => {
          const item = HARNESSES.find(harness => harness.id === id)!;
          return (
            <RadioGroup.Item key={id} value={id}
              className={cn('flex min-w-0 items-center gap-3 rounded-xl border border-border-subtle bg-bg-secondary px-3 py-2.5 text-left transition-[border-color,background-color,box-shadow] hover:border-border disabled:opacity-50 data-[state=checked]:border-primary-300 data-[state=checked]:bg-primary-50/60 data-[state=checked]:shadow-[0_0_0_3px_var(--color-primary-50)]', FOCUS_RING)}>
              <span aria-hidden className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[14px] font-semibold [font-family:var(--font-source)]', AVATAR[id])}>
                {item.label.slice(0, 1)}
              </span>
              <span className="min-w-0">
                <span className="block text-[13px] font-semibold leading-5 text-text-primary">{item.label}</span>
                {/* 末尾括号里的 CLI 名和卡片上的名字重复，卡片上省掉（悬停看全文） */}
                <span className="block text-[11.5px] leading-[1.45] text-text-muted" title={item.note}>{item.note.replace(/（[^（）]*）$/, '')}</span>
              </span>
            </RadioGroup.Item>
          );
        })}
      </RadioGroup.Root>
    </div>
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
      <FieldLabel className="mt-4">模型</FieldLabel>
      <ModelList key={value.harness} harness={value.harness} value={value.model} lastUsed={rememberedModel(value.harness)}
        disabled={disabled} onChange={model => onChange({ ...value, model })} />
    </div>
  );
}

/** 弹框里的小标题（「模型」） */
export function FieldLabel({ children, className }: { children: string; className?: string }) {
  return <div className={cn('mb-1.5 text-[11px] tracking-[0.12em] text-text-muted', className)}>{children}</div>;
}
