/** 跑任务用的 harness：服务器上的 Claude Code 或 Codex（都不需要逐条确认）。 */
export type Harness = 'claude' | 'codex';

export const HARNESSES: { id: Harness; label: string }[] = [
  { id: 'claude', label: 'Claude Code' },
  { id: 'codex', label: 'Codex' },
];

export function harnessLabel(harness: string | undefined): string {
  return harness === 'codex' ? 'Codex' : 'Claude';
}

const STORAGE_KEY = 'momo.agent.harness';

export function loadHarness(): Harness {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'codex' ? 'codex' : 'claude';
  } catch {
    return 'claude';
  }
}

export function saveHarness(harness: Harness): void {
  try {
    localStorage.setItem(STORAGE_KEY, harness);
  } catch {
    // 拿不到存储时只是下次不记得
  }
}
