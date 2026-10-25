/** 用哪个模型跑：服务器上的 Claude Code 或 Codex（都不需要逐条确认）。页面上只叫「模型」。 */
export type Harness = 'claude' | 'codex';

export const HARNESSES: { id: Harness; label: string; note: string }[] = [
  { id: 'claude', label: 'Claude', note: '用你的 Claude 订阅（Claude Code）' },
  { id: 'codex', label: 'Codex', note: '用你的 ChatGPT 订阅（Codex）；付费文章也肯全文翻' },
];

export function harnessLabel(harness: string | undefined): string {
  return harness === 'codex' ? 'Codex' : 'Claude';
}

const STORAGE_KEY = 'momo.agent.model';

/** 每个 Agent 记住上次选的模型；没选过就用它的默认 */
export function loadHarness(agent: string, fallback: Harness): Harness {
  try {
    const saved = (JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, string>)[agent];
    return saved === 'codex' || saved === 'claude' ? saved : fallback;
  } catch {
    return fallback;
  }
}

export function saveHarness(agent: string, harness: Harness): void {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, string>;
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...saved, [agent]: harness }));
  } catch {
    // 拿不到存储时只是下次不记得
  }
}
