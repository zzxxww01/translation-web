import { Fragment, type ReactNode } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { gridTemplate, PANES, type Collapsed } from '../lib/panes';
import { rowTextClass } from '../lib/rows';
import type { PaneId, WorkbenchRow } from '../types';
import { EditableText } from './EditableText';

const LINK = /\[([^\]]+)\]\(([^)\s]+)\)/g;

/** 原文里的 Markdown 链接渲染成链接，其余原样。 */
export function SourceText({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(LINK)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(text.slice(last, index));
    parts.push(
      <a key={index} href={match[2]} target="_blank" rel="noreferrer" className="text-primary-700 underline decoration-primary-200 underline-offset-2">
        {match[1]}
      </a>
    );
    last = index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

export interface PaneColumn {
  id: PaneId;
  /** 竖条上的栏名 */
  title: string;
  header: ReactNode;
  /** 中文栏：取这一行的译文、保存；英文栏不填 */
  text?: (row: WorkbenchRow) => string | null;
  save?: (row: WorkbenchRow, text: string) => Promise<void>;
  placeholder?: string;
  /** 「用另一版这段」的来源 */
  adopt?: { label: string; text: (row: WorkbenchRow) => string | null };
}

interface PaneGridProps {
  rows: WorkbenchRow[];
  columns: Record<PaneId, PaneColumn>;
  collapsed: Collapsed;
  onToggle: (pane: PaneId) => void;
  /** 手机上一次只显示一栏 */
  mobilePane: PaneId | null;
}

export function PaneGrid({ rows, columns, collapsed, onToggle, mobilePane }: PaneGridProps) {
  const visible = mobilePane ? [mobilePane] : PANES;
  const template = mobilePane ? 'minmax(0, 1fr)' : gridTemplate(collapsed);
  const isCollapsed = (id: PaneId) => !mobilePane && collapsed[id];

  return (
    <div className="min-h-0 flex-1 overflow-auto" data-testid="pane-grid">
      <div className="sticky top-0 z-20 grid border-b border-border-subtle bg-bg-primary/95 backdrop-blur" style={{ gridTemplateColumns: template }}>
        {visible.map(id => (
          <div key={id} className={cn('min-w-0 border-r border-border-subtle last:border-r-0', isCollapsed(id) && 'bg-bg-tertiary')}>
            {isCollapsed(id) ? (
              <button
                type="button"
                onClick={() => onToggle(id)}
                aria-label={`展开${columns[id].title}`}
                className="flex h-full min-h-[44px] w-full items-start justify-center py-3 text-text-muted hover:text-primary-700"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <div className="flex min-h-[44px] items-center gap-1 px-4 py-2">
                <div className="min-w-0 flex-1">{columns[id].header}</div>
                {!mobilePane && (
                  <button
                    type="button"
                    onClick={() => onToggle(id)}
                    aria-label={`收起${columns[id].title}`}
                    title="收起这一栏"
                    className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="grid pb-24" style={{ gridTemplateColumns: template }}>
        {rows.map((row, index) => (
          <Fragment key={row.key}>
            {visible.map(id => {
              if (isCollapsed(id)) {
                return (
                  <div key={id} className="border-r border-border-subtle bg-bg-tertiary last:border-r-0">
                    {index === 0 && (
                      <span className="sticky top-16 block py-3 text-center text-xs tracking-[0.3em] text-text-muted [writing-mode:vertical-rl]">
                        {columns[id].title}
                      </span>
                    )}
                  </div>
                );
              }
              return (
                <div key={id} className="min-w-0 border-r border-border-subtle px-5 py-2 last:border-r-0">
                  <Cell row={row} column={columns[id]} />
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

function Cell({ row, column }: { row: WorkbenchRow; column: PaneColumn }) {
  const textClass = rowTextClass(row);
  if (!column.text) {
    if (row.kind === 'image') {
      return row.image ? <img src={row.image} alt="" loading="lazy" className="my-2 max-h-72 w-auto max-w-full rounded border border-border-subtle" /> : null;
    }
    return (
      <div className={cn(textClass, row.kind === 'li' && 'pl-4 -indent-4 before:mr-2 before:content-["•"]')}>
        <SourceText text={row.source} />
      </div>
    );
  }
  if (row.kind === 'image') return <div className="py-2 text-xs text-text-disabled">（图片）</div>;
  const value = column.text(row);
  const other = column.adopt?.text(row);
  return (
    <div className={cn(textClass, row.kind === 'li' && 'flex gap-2 before:mt-1 before:content-["•"]')}>
      <EditableText
        id={`${column.id}:${row.key}`}
        value={value}
        placeholder={column.placeholder ?? ''}
        ariaLabel={`${column.title}：${row.source.slice(0, 40)}`}
        onSave={text => column.save!(row, text)}
        adopt={column.adopt && other ? { label: column.adopt.label, text: other } : null}
        className="min-w-0 flex-1"
      />
    </div>
  );
}
