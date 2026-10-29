import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { Harness } from '@/features/skills/harness';
import { cn } from '@/lib/utils';
import { loadAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { MEASURE, PRIMARY_BUTTON, STROKE } from '../lib/ui';
import { AgentChoiceFields } from './AgentCards';

/** 对照栏没有别的版本时：就地选 Agent 和模型开始翻。左边缘和栏头、正文的版心对齐。 */
export function CompareEmpty({ options, stopping, busy, error, onStart }: {
  options: Harness[];
  stopping: string | null;
  busy: boolean;
  error?: string | null;
  onStart: (choice: AgentChoice) => Promise<boolean>;
}) {
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice(undefined, options));
  return (
    <div className={cn(MEASURE, 'pb-10 pt-4')}><div className="max-w-[22rem]">
      <h3 className="text-[16px] font-semibold leading-snug text-text-primary [font-family:var(--font-display)]">选一个 Agent 翻这篇</h3>
      <p className="mb-4 mt-1.5 text-[12.5px] leading-relaxed text-text-muted">在服务器上跑 four-step-translate，关掉页面也不会停。翻好的译文会出现在这一栏。</p>
      <AgentChoiceFields options={options} value={choice} onChange={setChoice} disabled={busy} />
      {stopping && <p className="mt-3 text-[12px] leading-5 text-warning-text">会先停掉正在跑的 {stopping}。</p>}
      {error && <p role="alert" className="mt-3 text-[12px] leading-5 text-error">{error}</p>}
      <button type="button" disabled={busy} onClick={() => void onStart(choice)} className={cn(PRIMARY_BUTTON, 'mt-5 h-9 px-5 text-[13px]')}>
        {busy && <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" strokeWidth={STROKE} />}{busy ? '开始中…' : '开始翻译'}
      </button>
    </div></div>
  );
}
