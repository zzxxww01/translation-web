import { CheckCircle2, Circle, Download, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { fileUrl } from '../api';
import { useRunFiles } from '../hooks';
import { formatBytes } from '../state';
import type { RunStatus, TodoItem } from '../types';

function TodoIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle2 className="h-3.5 w-3.5 text-success" />;
  if (status === 'in_progress') return <Loader2 className="h-3.5 w-3.5 animate-spin text-primary-500" />;
  return <Circle className="h-3.5 w-3.5 text-text-muted" />;
}

export function SidePanel({ runId, status, todos }: { runId: string; status: RunStatus | null; todos: TodoItem[] }) {
  const { data: files = [] } = useRunFiles(runId, status);
  const outputs = files.filter(file => !file.path.startsWith('input/'));
  const inputs = files.filter(file => file.path.startsWith('input/'));

  return (
    <aside className="space-y-6 text-sm">
      <section>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">进度</h3>
        {todos.length === 0 ? (
          <p className="text-xs text-text-muted">Claude 列出步骤后会显示在这里</p>
        ) : (
          <ul className="space-y-1.5">
            {todos.map((todo, index) => (
              <li key={`${index}-${todo.content}`} className="flex items-start gap-2">
                <span className="mt-0.5 shrink-0">
                  <TodoIcon status={todo.status} />
                </span>
                <span className={cn('text-xs leading-relaxed', todo.status === 'completed' ? 'text-text-muted' : 'text-text-primary')}>
                  {todo.content}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">产出文件</h3>
        {outputs.length === 0 ? (
          <p className="text-xs text-text-muted">还没有产出</p>
        ) : (
          <FileList runId={runId} files={outputs} />
        )}
        {inputs.length > 0 && (
          <>
            <h3 className="mb-2 mt-5 text-xs font-medium uppercase tracking-wide text-text-muted">上传的文件</h3>
            <FileList runId={runId} files={inputs} />
          </>
        )}
      </section>
    </aside>
  );
}

function FileList({ runId, files }: { runId: string; files: { path: string; size: number }[] }) {
  return (
    <ul className="space-y-0.5">
      {files.map(file => (
        <li key={file.path}>
          <a
            href={fileUrl(runId, file.path)}
            download
            className="group flex items-center gap-2 rounded-md px-1.5 py-1 text-xs hover:bg-bg-hover"
            title={file.path}
          >
            <Download className="h-3.5 w-3.5 shrink-0 text-text-muted group-hover:text-primary-600" />
            <span className="min-w-0 flex-1 truncate text-text-primary">{file.path}</span>
            <span className="shrink-0 text-text-muted">{formatBytes(file.size)}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}
