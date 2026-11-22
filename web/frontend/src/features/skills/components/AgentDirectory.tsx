import { useMemo, useState } from 'react';
import { ArrowLeft, ChevronRight, FileCode2, FileText, MessageSquarePlus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { harnessLabel } from '../harness';
import { useSkillFile, useSkillFiles } from '../hooks';
import { renderMarkdown } from '../markdown';
import { formatBytes } from '../state';
import { agentKey } from '../agents';
import type { Agent } from '../types';
import { AgentAvatar } from './AgentIcon';

/** 全部 Agent：一行一个，点进去看名片和 skill 文件。以后加 Agent 只是多一行。 */
export function AgentList({ catalog, onOpen }: { catalog: Agent[]; onOpen: (agent: Agent) => void }) {
  return (
    <div className="mx-auto w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-10">
      <h1 className="text-2xl text-text-primary [font-family:var(--font-display)]">全部 Agent</h1>
      <p className="mt-1.5 text-sm text-text-muted">
        一个 Agent 就是一个 skill：服务器上一个文件夹，里面的 SKILL.md 写着它怎么干活。点进去可以看。
      </p>
      <ul className="mt-6 divide-y divide-border-subtle overflow-hidden rounded-xl border border-border-subtle bg-white">
        {catalog.map(agent => (
          <li key={agentKey(agent)}>
            <button
              type="button"
              onClick={() => onOpen(agent)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-bg-hover"
            >
              <AgentAvatar icon={agent.icon} />
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text-primary">{agent.title}</span>
                  {agent.name && <code className="truncate text-xs text-text-muted">{agent.name}</code>}
                  {!agent.available && <span className="text-xs text-error">未安装</span>}
                </span>
                <span className="mt-0.5 line-clamp-2 block text-xs leading-relaxed text-text-muted">{agent.description}</span>
              </span>
              <span className="hidden shrink-0 text-xs text-text-muted sm:inline">默认 {harnessLabel(agent.harness)}</span>
              <ChevronRight className="h-4 w-4 shrink-0 text-text-muted" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface AgentDetailProps {
  agent: Agent;
  onBack: () => void;
  onStart: (agent: Agent) => void;
}

/** 一个 Agent：名片（干什么、怎么说）+ skill 文件（SKILL.md 和脚本、参考资料，只读） */
export function AgentDetail({ agent, onBack, onStart }: AgentDetailProps) {
  return (
    <div className="mx-auto w-full max-w-5xl px-5 py-6 sm:px-8">
      <Button variant="ghost" size="sm" onClick={onBack} className="-ml-2">
        <ArrowLeft /> 全部 Agent
      </Button>
      <div className="mt-3 flex flex-wrap items-start gap-4">
        <AgentAvatar icon={agent.icon} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="text-xl text-text-primary [font-family:var(--font-display)]">{agent.title}</h1>
          <p className="mt-1 text-sm leading-relaxed text-text-secondary">{agent.description}</p>
          <p className="mt-1.5 text-xs text-text-muted">
            {agent.name ? <>skill：<code>{agent.name}</code> · </> : null}默认用 {harnessLabel(agent.harness)} 跑
          </p>
        </div>
        <Button onClick={() => onStart(agent)} disabled={!agent.available}>
          <MessageSquarePlus /> 和它对话
        </Button>
      </div>

      {(agent.hint || agent.examples.length > 0) && (
        <section className="mt-6 rounded-xl border border-border-subtle bg-white px-4 py-3">
          <h2 className="text-xs font-medium text-text-secondary">怎么用</h2>
          {agent.hint && <p className="mt-1 text-sm text-text-primary">{agent.hint}</p>}
          {agent.examples.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-2">
              {agent.examples.map(example => (
                <li key={example} className="rounded-full bg-bg-secondary px-3 py-1 text-xs text-text-secondary">{example}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {agent.name ? (
        <SkillFiles name={agent.name} />
      ) : (
        <p className="mt-6 text-sm text-text-muted">通用 Agent 什么都能聊；遇到翻译、字幕这类专门的活，它会提醒你换对应的 Agent。</p>
      )}
    </div>
  );
}

function SkillFiles({ name }: { name: string }) {
  const listing = useSkillFiles(name);
  const files = useMemo(() => listing.data?.files ?? [], [listing.data]);
  const [picked, setPicked] = useState<string | null>(null);
  const current = picked ?? files[0]?.path ?? null;

  if (listing.isPending) return <p className="mt-6 text-sm text-text-muted">读取 skill 文件…</p>;
  if (listing.error) return <p className="mt-6 text-sm text-error">读不了 skill 文件：{listing.error.message}</p>;

  return (
    <section className="mt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium text-text-primary">Skill 文件</h2>
        <code className="text-xs text-text-muted">{listing.data?.root}</code>
      </div>
      <div className="mt-2 flex min-h-[24rem] flex-col overflow-hidden rounded-xl border border-border-subtle bg-white md:flex-row">
        <ul className="max-h-60 shrink-0 overflow-y-auto border-b border-border-subtle py-1 md:max-h-[70vh] md:w-64 md:border-b-0 md:border-r">
          {files.map(file => (
            <li key={file.path}>
              <button
                type="button"
                onClick={() => setPicked(file.path)}
                title={file.path}
                className={cn(
                  'flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors',
                  file.path === current ? 'bg-primary-50 text-text-primary' : 'text-text-secondary hover:bg-bg-hover'
                )}
              >
                {file.path.endsWith('.md') ? <FileText className="h-3.5 w-3.5 shrink-0" /> : <FileCode2 className="h-3.5 w-3.5 shrink-0" />}
                <span className="min-w-0 flex-1 truncate">{file.path}</span>
                <span className="shrink-0 text-text-muted">{formatBytes(file.size)}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="min-w-0 flex-1 overflow-auto md:max-h-[70vh]">
          {current ? <FileView name={name} path={current} /> : <p className="p-4 text-sm text-text-muted">没有文件</p>}
        </div>
      </div>
    </section>
  );
}

/** SKILL.md 开头的 frontmatter 单独显示成代码块，正文按 Markdown 排版 */
function splitFrontmatter(text: string): { front: string | null; body: string } {
  const match = /^---\n([\s\S]*?)\n---\n?/.exec(text);
  return match ? { front: match[1], body: text.slice(match[0].length) } : { front: null, body: text };
}

function FileView({ name, path }: { name: string; path: string }) {
  const file = useSkillFile(name, path);
  const markdown = path.endsWith('.md');
  const parts = useMemo(() => (file.data && markdown ? splitFrontmatter(file.data.content) : null), [file.data, markdown]);
  const html = useMemo(() => (parts ? renderMarkdown(parts.body) : ''), [parts]);

  if (file.isPending) return <p className="p-4 text-sm text-text-muted">读取中…</p>;
  if (file.error) return <p className="p-4 text-sm text-text-muted">{file.error.message}</p>;
  if (parts) {
    return (
      <div className="px-5 py-4">
        {parts.front && (
          <pre className="mb-4 whitespace-pre-wrap break-words rounded-lg bg-bg-secondary px-3 py-2 text-xs text-text-secondary">{parts.front}</pre>
        )}
        {/* html 已经过 DOMPurify 消毒 */}
        <div className="skill-md text-sm text-text-primary" dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    );
  }
  return <pre className="whitespace-pre px-4 py-3 text-xs leading-relaxed text-text-primary">{file.data.content}</pre>;
}
