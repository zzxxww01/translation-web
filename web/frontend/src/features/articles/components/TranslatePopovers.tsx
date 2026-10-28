import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { Harness } from '@/features/skills/harness';
import { articlesApi } from '../api';
import { articleKeys } from '../hooks';
import { loadAgentChoice, rememberedModel, type AgentChoice } from '../lib/agentChoice';
import type { VersionView } from '../lib/versions';
import { AgentChoiceFields } from './AgentCards';
import { ModelList } from './ModelList';

const CONTENT = 'w-[320px] rounded-[14px] border-0 p-[18px] shadow-[0_0_0_1px_rgba(43,39,48,0.06),0_18px_48px_rgba(43,39,48,0.16)]';

function Warning({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3.5 flex gap-2 rounded-[10px] bg-warning-light px-3 py-2.5 text-[12px] leading-relaxed text-[#7a520f]">
      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

function Shell({ title, sub, children, confirmLabel, busy, onCancel, onConfirm }: {
  title: string; sub: string; children: ReactNode; confirmLabel: string; busy: boolean; onCancel: () => void; onConfirm: () => void;
}) {
  return (
    <>
      <h4 className="text-[15.5px] font-semibold text-text-primary [font-family:var(--font-display)]">{title}</h4>
      <p className="mb-3.5 mt-0.5 text-[12px] text-text-muted">{sub}</p>
      {children}
      <div className="mt-4 flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-[34px] rounded-full px-3.5 text-[13px] text-text-secondary hover:bg-bg-hover">取消</button>
        <button type="button" disabled={busy} onClick={onConfirm}
          className="inline-flex h-[34px] items-center gap-1.5 rounded-full bg-primary-500 px-4 text-[13px] font-medium text-white shadow-[0_1px_2px_rgba(116,42,79,0.25),0_4px_12px_rgba(163,61,112,0.18)] hover:bg-primary-600 disabled:opacity-60">
          {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {busy ? '开始中…' : confirmLabel}
        </button>
      </div>
    </>
  );
}

/** Agent 版的「↻ 重新翻译」：Agent 固定，只换模型。onConfirm 成功返回 true 才关框。 */
export function RetranslatePopover({ projectId, version, stopping, busy, onConfirm, children }: {
  projectId: string;
  version: VersionView;
  /** 正在跑、会被先停掉的 Agent 名 */
  stopping: string | null;
  busy: boolean;
  onConfirm: (model: string) => Promise<boolean>;
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
    <Popover open={open} onOpenChange={next => { setOpen(next); if (next) setModel(rememberedModel(harness)); }}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="end" className={CONTENT}>
        <Shell title={`重新翻译 ${version.name} 版`} sub="在服务器上跑，关掉页面也不会停" confirmLabel="重新翻译"
          busy={busy} onCancel={() => setOpen(false)} onConfirm={() => void confirm()}>
          <div className="mb-1.5 text-[11px] tracking-[0.12em] text-text-muted">模型</div>
          <ModelList harness={harness} value={model} onChange={setModel} lastUsed={rememberedModel(harness)} disabled={busy} />
          {version.variant && (
            <Warning>
              {`翻完会整篇替换现在的 ${version.name} 版`}
              {edited > 0 ? `，你改过的 ${edited} 段也会被替换` : ''}
              ；翻完前这一版只读。
            </Warning>
          )}
          {stopping && <Warning>{`会先停掉正在跑的 ${stopping}。`}</Warning>}
        </Shell>
      </PopoverContent>
    </Popover>
  );
}

/** 对照栏标签末尾的「＋」：只列还没有译本的 Agent */
export function AddAgentPopover({ options, stopping, busy, onConfirm, children }: {
  options: Harness[];
  stopping: string | null;
  busy: boolean;
  onConfirm: (choice: AgentChoice) => Promise<boolean>;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice(undefined, options));
  const confirm = async () => {
    if (await onConfirm(choice)) setOpen(false);
  };
  return (
    <Popover open={open} onOpenChange={next => { setOpen(next); if (next) setChoice(loadAgentChoice(undefined, options)); }}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="start" className={CONTENT}>
        <Shell title="用 Agent 再翻一版" sub="只列出还没有译本的 Agent" confirmLabel="开始翻译"
          busy={busy} onCancel={() => setOpen(false)} onConfirm={() => void confirm()}>
          <AgentChoiceFields options={options} value={choice} onChange={setChoice} disabled={busy} />
          {stopping && <Warning>{`会先停掉正在跑的 ${stopping}。`}</Warning>}
        </Shell>
      </PopoverContent>
    </Popover>
  );
}
