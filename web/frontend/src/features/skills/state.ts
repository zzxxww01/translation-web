import type { Answers, Question, RunStatus, SkillEvent, TodoItem } from './types';

export interface ToolCall {
  id: string;
  name: string;
  summary: string;
  result?: { ok: boolean; text: string };
  /** 子代理（Agent 工具）内部的调用挂在发起它的那次调用下面 */
  children: ToolCall[];
}

export type ChatItem =
  | { kind: 'user'; key: string; text: string; files: string[] }
  | { kind: 'text'; key: string; text: string }
  | { kind: 'tools'; key: string; tools: ToolCall[] }
  | { kind: 'question'; key: string; qid: string; questions: Question[]; answer?: { answers?: Answers; response?: string } }
  | { kind: 'notice'; key: string; level: 'info' | 'warn' | 'error'; text: string }
  | { kind: 'turn'; key: string; durationMs: number; isError: boolean; errors: string[] };

export interface RunView {
  items: ChatItem[];
  todos: TodoItem[];
  status: RunStatus | null;
  error: string | null;
  pendingQids: string[];
  lastSeq: number;
}

export const EMPTY_VIEW: RunView = { items: [], todos: [], status: null, error: null, pendingQids: [], lastSeq: 0 };

/** 把事件流折叠成页面要画的东西。纯函数，每次都从头算，事件量在几千以内足够快。 */
export function foldEvents(events: SkillEvent[]): RunView {
  const items: ChatItem[] = [];
  const tools = new Map<string, ToolCall>();
  const questions = new Map<string, Extract<ChatItem, { kind: 'question' }>>();
  const pending = new Set<string>();
  let todos: TodoItem[] = [];
  let status: RunStatus | null = null;
  let error: string | null = null;
  let lastSeq = 0;

  for (const event of events) {
    lastSeq = Math.max(lastSeq, event.seq);
    const key = String(event.seq);
    switch (event.type) {
      case 'user':
        items.push({ kind: 'user', key, text: event.text, files: event.files });
        break;
      case 'text':
        if (!event.parent) items.push({ kind: 'text', key, text: event.text });
        break;
      case 'tool': {
        const call: ToolCall = { id: event.id, name: event.name, summary: event.summary, children: [] };
        tools.set(call.id, call);
        const parent = event.parent ? tools.get(event.parent) : undefined;
        if (parent) {
          parent.children.push(call);
          break;
        }
        const last = items[items.length - 1];
        if (last?.kind === 'tools') last.tools.push(call);
        else items.push({ kind: 'tools', key, tools: [call] });
        break;
      }
      case 'tool_result': {
        const call = tools.get(event.id);
        if (call) call.result = { ok: event.ok, text: event.text };
        break;
      }
      case 'question': {
        const item = { kind: 'question' as const, key, qid: event.qid, questions: event.questions };
        questions.set(event.qid, item);
        pending.add(event.qid);
        items.push(item);
        break;
      }
      case 'answer': {
        const item = questions.get(event.qid);
        if (item) item.answer = { answers: event.answers, response: event.response };
        pending.delete(event.qid);
        break;
      }
      case 'todos':
        todos = event.items;
        break;
      case 'status':
        status = event.status;
        error = event.error;
        if (event.status !== 'waiting') {
          // 中断、出错、重启后，没答的提问都已失效
          if (event.status !== 'running') pending.clear();
        }
        break;
      case 'result':
        items.push({ kind: 'turn', key, durationMs: event.duration_ms, isError: event.is_error, errors: event.errors });
        break;
      case 'notice':
        items.push({ kind: 'notice', key, level: event.level, text: event.text });
        break;
      case 'error':
        items.push({ kind: 'notice', key, level: 'error', text: event.text });
        break;
    }
  }

  return { items, todos, status, error, pendingQids: [...pending], lastSeq };
}

/** 合并新事件：按 seq 去重、保序（断线重连可能重放一段）。 */
export function mergeEvents(current: SkillEvent[], incoming: SkillEvent[]): SkillEvent[] {
  const last = current.length ? current[current.length - 1].seq : 0;
  const fresh = incoming.filter(event => event.seq > last).sort((a, b) => a.seq - b.seq);
  return fresh.length ? [...current, ...fresh] : current;
}

export const STATUS_LABEL: Record<RunStatus, string> = {
  running: '运行中',
  waiting: '等你回答',
  idle: '等你回复',
  error: '已中断',
};

export function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 ** 2) return `${(size / 1024).toFixed(1)} KB`;
  if (size < 1024 ** 3) return `${(size / 1024 ** 2).toFixed(1)} MB`;
  return `${(size / 1024 ** 3).toFixed(2)} GB`;
}

export function formatDuration(ms: number): string {
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds} 秒`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分 ${seconds % 60} 秒`;
  return `${Math.floor(minutes / 60)} 小时 ${minutes % 60} 分`;
}
