import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { Harness } from '@/features/skills/harness';
import { loadAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { AgentChoiceFields } from './AgentCards';

/** 对照栏没有别的版本时：就地选 Agent 和模型开始翻 */
export function CompareEmpty({ options, stopping, busy, onStart }: {
  options: Harness[];
  stopping: string | null;
  busy: boolean;
  onStart: (choice: AgentChoice) => Promise<boolean>;
}) {
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice(undefined, options));
  return (
    <div className="mx-auto max-w-[360px] py-10">
      <h3 className="text-[16px] font-semibold text-text-primary [font-family:var(--font-display)]">选一个 Agent 翻这篇</h3>
      <p className="mb-4 mt-1 text-[12.5px] leading-relaxed text-text-muted">在服务器上跑 four-step-translate，关掉页面也不会停。翻好的译文会出现在这一栏。</p>
      <AgentChoiceFields options={options} value={choice} onChange={setChoice} disabled={busy} />
      {stopping && <p className="mt-3 text-[12px] text-[#7a520f]">会先停掉正在跑的 {stopping}。</p>}
      <button type="button" disabled={busy} onClick={() => void onStart(choice)}
        className="mt-4 inline-flex h-9 items-center gap-1.5 rounded-full bg-primary-500 px-5 text-[13px] font-medium text-white shadow-[0_1px_2px_rgba(116,42,79,0.25),0_4px_12px_rgba(163,61,112,0.18)] hover:bg-primary-600 disabled:opacity-60">
        {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}{busy ? '开始中…' : '开始翻译'}
      </button>
    </div>
  );
}
