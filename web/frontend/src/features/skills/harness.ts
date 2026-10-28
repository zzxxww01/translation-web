/** 服务器上执行任务的运行工具；具体模型单独选择。 */
export type Harness = 'claude' | 'codex' | 'antigravity';

export const HARNESSES: { id: Harness; label: string; note: string }[] = [
  { id: 'claude', label: 'Claude', note: '用你的 Claude 订阅（Claude Code）' },
  { id: 'codex', label: 'Codex', note: '用你的 ChatGPT 订阅（Codex）' },
  // 内部 id 仍是 antigravity（服务器上的 agy CLI），界面上叫 Gemini
  { id: 'antigravity', label: 'Gemini', note: '用服务器上登录的 Google 账号（Gemini）' },
];

export function harnessLabel(harness: string | undefined): string {
  return HARNESSES.find(item => item.id === harness)?.label ?? 'Claude';
}

const STORAGE_KEY = 'momo.agent.model';

/** 每个 Agent 记住上次选的模型；没选过就用它的默认 */
export function loadHarness(agent: string, fallback: Harness): Harness {
  try {
    const saved = (JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, string>)[agent];
    return saved === 'codex' || saved === 'claude' || saved === 'antigravity' ? saved : fallback;
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
