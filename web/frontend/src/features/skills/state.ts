import type { Answers, HeldMessage, Question, RunStatus, SkillEvent, TodoItem } from './types';

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
  | { kind: 'report'; key: string; title: string; lines: string[] }
  | { kind: 'turn'; key: string; durationMs: number; isError: boolean; errors: string[] };

export interface RunView {
  items: ChatItem[];
  todos: TodoItem[];
  status: RunStatus | null;
  /** 停下来是在等你确认（不是做完了） */
  awaiting: boolean;
  error: string | null;
  pendingQids: string[];
  /** 挂起待发的消息；null = 事件流里还没出现过（旧对话），用 meta 里的 */
  held: HeldMessage[] | null;
  /** 挂起的消息停住了（上一轮没正常结束），不会自动发 */
  heldPaused: boolean;
  lastSeq: number;
}

export const EMPTY_VIEW: RunView = { items: [], todos: [], status: null, awaiting: false, error: null, pendingQids: [], held: null, heldPaused: false, lastSeq: 0 };

// Agent 在等你确认时回复末尾带的标记（见 skill_runner/runner.py 的 AWAIT_MARK）；页面上用状态表示，不显示这行字
const AWAIT_MARK = /\n?[ \t]*【等待确认】[ \t]*$/;
const AUTO_REPLY_NOTICE = /内没有回复，会自动按推荐方案继续$/;

/** 把事件流折叠成页面要画的东西。纯函数，每次都从头算，事件量在几千以内足够快。 */
export function foldEvents(events: SkillEvent[]): RunView {
  const items: ChatItem[] = [];
  const tools = new Map<string, ToolCall>();
  const questions = new Map<string, Extract<ChatItem, { kind: 'question' }>>();
  const pending = new Set<string>();
  let todos: TodoItem[] = [];
  let held: HeldMessage[] | null = null;
  let heldPaused = false;
  let status: RunStatus | null = null;
  let awaiting = false;
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
        if (!event.parent) items.push({ kind: 'text', key, text: event.text.replace(AWAIT_MARK, '') });
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
      case 'held':
        held = event.items;
        heldPaused = Boolean(event.paused);
        break;
      case 'report':
        items.push({ kind: 'report', key, title: event.title, lines: event.lines });
        break;
      case 'status':
        status = event.status;
        awaiting = Boolean(event.awaiting);
        error = event.error;
        // 中断、出错后，没答的提问都已失效。例外：提问挂太久时服务端关掉了进程（idle + awaiting），
        // 问题仍可回答，回答会作为新消息续接
        if (event.status !== 'waiting' && event.status !== 'running' && !(event.status === 'idle' && event.awaiting)) {
          pending.clear();
        }
        break;
      case 'result':
        items.push({ kind: 'turn', key, durationMs: event.duration_ms, isError: event.is_error, errors: event.errors });
        break;
      case 'notice':
        // 「N 分钟内没有回复，会自动按推荐方案继续」：输入框上方那行已经写了几点自动继续，不再占一行
        if (!AUTO_REPLY_NOTICE.test(event.text)) items.push({ kind: 'notice', key, level: event.level, text: event.text });
        break;
      case 'error':
        items.push({ kind: 'notice', key, level: 'error', text: event.text });
        break;
    }
  }

  return { items, todos, status, awaiting, error, pendingQids: [...pending], held, heldPaused, lastSeq };
}

/** 合并新事件：按 seq 去重、保序（断线重连可能重放一段）。 */
export function mergeEvents(current: SkillEvent[], incoming: SkillEvent[]): SkillEvent[] {
  const last = current.length ? current[current.length - 1].seq : 0;
  const fresh = incoming.filter(event => event.seq > last).sort((a, b) => a.seq - b.seq);
  return fresh.length ? [...current, ...fresh] : current;
}

/** 页面上只说五种状态：排队中、进行中、等你确认（提问挂着，或说完在等你确认）、完成、已中断 */
export type DisplayStatus = 'queued' | 'running' | 'waiting' | 'done' | 'error';

export function displayStatus(status: RunStatus | null, awaiting?: boolean): DisplayStatus | null {
  if (!status) return null;
  if (status === 'waiting' || (status === 'idle' && awaiting)) return 'waiting';
  return status === 'idle' ? 'done' : status;
}

export const STATUS_LABEL: Record<DisplayStatus, string> = {
  queued: '排队中',
  running: '进行中',
  waiting: '等你确认',
  done: '完成',
  error: '已中断',
};

/** 对话标题：旧对话的标题是整句指令（「精翻附件里的这篇文章。输出目录放在…」），太长就只留第一句 */
export function runTitle(title: string): string {
  const first = title.split('。')[0].trim();
  return title.length > 30 && first ? first : title;
}

/** 「按建议继续」替你发的话 */
export const CONTINUE_TEXT = '确认，按你的建议继续。';

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
