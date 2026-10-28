import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { Harness } from '@/features/skills/harness';
import { articlesApi } from '../api';
import { articleKeys } from '../hooks';
import { loadAgentChoice, rememberedModel, type AgentChoice } from '../lib/agentChoice';
import type { VersionView } from '../lib/versions';
import { cn } from '@/lib/utils';
import { FOCUS_RING, PRIMARY_BUTTON, STROKE } from '../lib/ui';
import { AgentChoiceFields, FieldLabel } from './AgentCards';
import { ModelList } from './ModelList';

/** 宽 320、圆角 14、阴影比纸张深一级（设计文档 6.5）；超出屏幕高度时内部滚动 */
const CONTENT = 'wb-pop w-[320px] max-w-[calc(100vw-24px)] max-h-[var(--radix-popover-content-available-height)] overflow-y-auto rounded-[14px] border-0 p-[18px] shadow-pop';

/** 有几条警告写几句，但只用一个框：两个黄框叠在一起太重 */
function Warnings({ items }: { items: (string | false | null | undefined)[] }) {
  const lines = items.filter((item): item is string => Boolean(item));
  if (!lines.length) return null;
  return (
    <div className="mt-3.5 flex gap-2 rounded-[10px] bg-warning-light px-3 py-2.5 text-[12px] leading-relaxed text-warning-text">
      <AlertCircle aria-hidden className="mt-[3px] h-3.5 w-3.5 shrink-0" strokeWidth={STROKE} />
      <div className="space-y-1">{lines.map(line => <p key={line}>{line}</p>)}</div>
    </div>
  );
}

function Shell({ title, sub, children, confirmLabel, busy, onCancel, onConfirm }: {
  title: string; sub: string; children: ReactNode; confirmLabel: string; busy: boolean; onCancel: () => void; onConfirm: () => void;
}) {
  return (
    <>
      <h4 className="text-[15.5px] font-semibold leading-snug text-text-primary [font-family:var(--font-display)]">{title}</h4>
      <p className="mb-4 mt-1 text-[12px] leading-5 text-text-muted">{sub}</p>
      {children}
      <div className="mt-[18px] flex justify-end gap-1.5">
        <button type="button" onClick={onCancel}
          className={cn('h-[34px] rounded-full px-3.5 text-[13px] text-text-secondary transition-colors hover:bg-ink-wash hover:text-text-primary', FOCUS_RING)}>取消</button>
        <button type="button" disabled={busy} onClick={onConfirm} className={cn(PRIMARY_BUTTON, 'h-[34px] px-[18px] text-[13px]')}>
          {busy && <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" strokeWidth={STROKE} />}
          {busy ? '开始中…' : confirmLabel}
        </button>
      </div>
    </>
  );
}

/** Agent 版的「↻ 重新翻译」：Agent 固定，只换模型。onConfirm 成功返回 true 才关框。 */
export function RetranslatePopover({ projectId, version, stopping, busy, error, onConfirm, onOpen, children }: {
  projectId: string;
  version: VersionView;
  /** 正在跑、会被先停掉的 Agent 名 */
  stopping: string | null;
  busy: boolean;
  /** 上一次没能开始的原因，写在弹框里 */
  error?: string | null;
  onConfirm: (model: string) => Promise<boolean>;
  /** 打开时（清掉上一次的错误） */
  onOpen?: () => void;
  children: ReactNode;
}) {
  const harness = version.harness as Harness;
  const [open, setOpen] = useState(false);
  const [model, setModel] = useState('');
  const changes = useQuery({
    queryKey: articleKeys.changes(version.id),
    queryFn: () => articlesApi.changes(projectId, version.id),
    enabled: open && Boolean(version.variant),
    retry: false,
  });
  const edited = changes.data?.changed ?? 0;
  const confirm = async () => {
    if (await onConfirm(model)) setOpen(false);
  };
  return (
    <Popover open={open} onOpenChange={next => { setOpen(next); if (next) { setModel(rememberedModel(harness)); onOpen?.(); } }}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="end" sideOffset={6} collisionPadding={12} className={CONTENT}>
        <Shell title={`重新翻译 ${version.name} 版`} sub="在服务器上跑，关掉页面也不会停" confirmLabel="重新翻译"
          busy={busy} onCancel={() => setOpen(false)} onConfirm={() => void confirm()}>
          <FieldLabel>模型</FieldLabel>
          <ModelList harness={harness} value={model} onChange={setModel} lastUsed={rememberedModel(harness)} disabled={busy} />
          <Warnings items={[
            version.variant && `翻完会整篇替换现在的 ${version.name} 版${edited > 0 ? `，你改过的 ${edited} 段也会被替换` : ''}；翻完前这一版只读。`,
            stopping && `会先停掉正在跑的 ${stopping}。`,
          ]} />
          {error && <p role="alert" className="mt-3 text-[12px] leading-5 text-error">{error}</p>}
        </Shell>
      </PopoverContent>
    </Popover>
  );
}

/** 对照栏标签末尾的「＋」：只列还没有译本的 Agent */
export function AddAgentPopover({ options, stopping, busy, error, onConfirm, onOpen, children }: {
  options: Harness[];
  stopping: string | null;
  busy: boolean;
  error?: string | null;
  onConfirm: (choice: AgentChoice) => Promise<boolean>;
  onOpen?: () => void;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice(undefined, options));
  const confirm = async () => {
    if (await onConfirm(choice)) setOpen(false);
  };
  return (
    <Popover open={open} onOpenChange={next => { setOpen(next); if (next) { setChoice(loadAgentChoice(undefined, options)); onOpen?.(); } }}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="start" sideOffset={6} collisionPadding={12} className={CONTENT}>
        <Shell title="用 Agent 再翻一版" sub="只列出还没有译本的 Agent" confirmLabel="开始翻译"
          busy={busy} onCancel={() => setOpen(false)} onConfirm={() => void confirm()}>
          <AgentChoiceFields options={options} value={choice} onChange={setChoice} disabled={busy} />
          <Warnings items={[stopping && `会先停掉正在跑的 ${stopping}。`]} />
          {error && <p role="alert" className="mt-3 text-[12px] leading-5 text-error">{error}</p>}
        </Shell>
      </PopoverContent>
    </Popover>
  );
}
