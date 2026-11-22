/** skill-runner（/api/skills）的数据结构，与 skill_runner/ 后端一一对应。 */
import type { Harness } from './harness';

/** queued：名额满了在排队，有空位自动开始 */
export type RunStatus = 'running' | 'waiting' | 'idle' | 'error' | 'queued';

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
  harness?: Harness;
  model?: string | null;
  actual_model?: string | null;
  /** 等确认时多少秒没回复就自动按推荐方案继续，0 = 一直等 */
  auto_reply_s?: number;
  /** 上一轮结束时在等你确认（不是做完了） */
  awaiting_reply?: boolean;
  /** 到这个时间（epoch 秒）还没回复就自动继续 */
  auto_reply_at?: number | null;
  /** 谁开的：空 = Claude 页；slack:<会话>[:<thread_ts>] = momo Slack 页给会话 / thread 配的 agent */
  source?: string;
  /** 排队开始的时间（epoch 秒）；不在排队时为 null */
  queued_at?: number | null;
  /** 挂起的消息：agent 干活时发的话，这一轮结束后按顺序发 */
  held?: HeldMessage[];
}

export interface HeldMessage {
  id: string;
  text: string;
  files: string[];
  created_at: number;
}

/** Agent 详情页：skill 目录里的文件 */
export interface SkillFiles {
  /** 服务器上的目录（~ 开头） */
  root: string;
  files: { path: string; size: number }[];
}

/** 页面上的一个 Agent（名片来自 skill_runner/agents.json）。name 是 skill 名，空串是通用 Agent（直接对话）。 */
export interface Agent {
  name: string;
  title: string;
  icon: string;
  description: string;
  /** 要给它什么（输入框的提示） */
  hint: string;
  examples: string[];
  /** 新对话默认用哪个模型跑 */
  harness: Harness;
  available: boolean;
}

export interface RunFile {
  path: string;
  size: number;
  mtime: number;
}

export interface ModelCatalog {
  models: { id: string; label: string; description: string }[];
  default_model: string | null;
  source: 'cache' | 'runtime' | 'aliases' | 'unavailable';
  warning: string | null;
}

export interface RuntimeUpdateSnapshot {
  active: boolean;
  checking: boolean;
  checked_at: number | null;
  runtimes: {
    harness: Harness;
    label: string;
    current: string | null;
    latest: string | null;
    update_available: boolean;
    can_update: boolean;
    reason: string | null;
    error: string | null;
    status: 'unchecked' | 'ready' | 'updating' | 'succeeded' | 'failed';
    message: string | null;
    updated_at: number | null;
  }[];
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
    | { type: 'held'; items: HeldMessage[] }
    /** 页面命令（/status）的回答，服务端直接给，不经过模型 */
    | { type: 'report'; title: string; lines: string[] }
    | { type: 'status'; status: RunStatus; error: string | null; awaiting?: boolean }
    | { type: 'result'; is_error: boolean; subtype: string; duration_ms: number; num_turns: number; errors: string[] }
    | { type: 'notice'; level: 'info' | 'warn' | 'error'; text: string }
    | { type: 'error'; text: string }
  );

export interface TodoItem {
  content: string;
  status: string;
}
