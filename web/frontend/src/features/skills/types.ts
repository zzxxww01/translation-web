/** skill-runner（/api/skills）的数据结构，与 skill_runner/ 后端一一对应。 */

export type RunStatus = 'running' | 'waiting' | 'idle' | 'error';

export interface RunMeta {
  id: string;
  skill: string;
  title: string;
  status: RunStatus;
  created_at: number;
  updated_at: number;
  session_id: string | null;
  error: string | null;
  /** 旧任务没有这个字段，按 Claude 处理 */
  harness?: 'claude' | 'codex';
  /** 等确认时多少秒没回复就自动按推荐方案继续，0 = 一直等 */
  auto_reply_s?: number;
  /** 上一轮结束时在等你确认（不是做完了） */
  awaiting_reply?: boolean;
  /** 到这个时间（epoch 秒）还没回复就自动继续 */
  auto_reply_at?: number | null;
}

/** 页面上的一个 agent（名片来自 skill_runner/agents.json）。name 是 skill 名，空串表示直接和 Claude 聊天。 */
export interface Agent {
  name: string;
  title: string;
  icon: string;
  description: string;
  hint: string;
  examples: string[];
  available: boolean;
}

export interface RunFile {
  path: string;
  size: number;
  mtime: number;
}

export interface QuestionOption {
  label: string;
  description?: string;
}

export interface Question {
  question: string;
  header?: string;
  options: QuestionOption[];
  multiSelect?: boolean;
}

export type Answers = Record<string, string | string[]>;

interface Base {
  seq: number;
  ts: number;
}

export type SkillEvent = Base &
  (
    | { type: 'user'; text: string; files: string[] }
    | { type: 'text'; text: string; parent: string | null }
    | { type: 'tool'; id: string; name: string; summary: string; parent: string | null }
    | { type: 'tool_result'; id: string; ok: boolean; text: string; parent: string | null }
    | { type: 'question'; qid: string; questions: Question[] }
    | { type: 'answer'; qid: string; answers?: Answers; response?: string }
    | { type: 'todos'; items: TodoItem[] }
    | { type: 'status'; status: RunStatus; error: string | null }
    | { type: 'result'; is_error: boolean; subtype: string; duration_ms: number; num_turns: number; errors: string[] }
    | { type: 'notice'; level: 'info' | 'warn' | 'error'; text: string }
    | { type: 'error'; text: string }
  );

export interface TodoItem {
  content: string;
  status: string;
}
