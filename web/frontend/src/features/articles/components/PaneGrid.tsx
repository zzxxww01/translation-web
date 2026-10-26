import { Fragment, useEffect, useRef, type ReactNode } from 'react';
import { Bookmark, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { gridTemplate, PANES, type Collapsed } from '../lib/panes';
import { rowTextClass } from '../lib/rows';
import type { PaneId, WorkbenchRow } from '../types';
import { EditableText } from './EditableText';
import { InlineMarkdown } from './InlineMarkdown';

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
  readingKey?: string | null;
  markBusy: boolean;
  onMark: (key: string) => void;
  jump: number;
}

/** Only reunite adjacent pieces from the same source paragraph, never headings or list items. */
function readingBlocks(rows: WorkbenchRow[]): WorkbenchRow[][] {
  const blocks: WorkbenchRow[][] = [];
  for (const row of rows) {
    const previous = blocks.at(-1)?.at(-1);
    if (row.kind === 'p' && row.block && previous?.kind === 'p' &&
        previous.block === row.block && previous.section_id === row.section_id &&
        Boolean(previous.is_metadata) === Boolean(row.is_metadata)) {
      blocks[blocks.length - 1].push(row);
    } else blocks.push([row]);
  }
  return blocks;
}

export function PaneGrid({ rows, columns, collapsed, onToggle, mobilePane, readingKey, markBusy, onMark, jump }: PaneGridProps) {
  const visible = mobilePane ? [mobilePane] : PANES;
  const template = mobilePane ? 'minmax(0, 1fr)' : gridTemplate(collapsed);
  const isCollapsed = (id: PaneId) => !mobilePane && collapsed[id];
  const container = useRef<HTMLDivElement>(null);
  const lastJump = useRef(0);
  useEffect(() => {
    if (jump === lastJump.current) return;
    lastJump.current = jump;
    container.current?.querySelectorAll('[data-reading-mark="true"]').forEach(element => {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }, [jump]);
  const blocks = readingBlocks(rows);

  return (
    <div ref={container} className="flex min-h-0 flex-1 flex-col overflow-hidden" data-testid="pane-grid">
      <div className="z-20 grid shrink-0 border-b border-border-subtle bg-bg-primary/95 backdrop-blur" style={{ gridTemplateColumns: template }}>
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

      <div className="grid min-h-0 flex-1" style={{ gridTemplateColumns: template }}>
        {visible.map(id => isCollapsed(id) ? (
          <div key={id} className="border-r border-border-subtle bg-bg-tertiary last:border-r-0">
            <span className="block py-3 text-center text-xs tracking-[0.3em] text-text-muted [writing-mode:vertical-rl]">{columns[id].title}</span>
          </div>
        ) : (
          <article key={id} aria-label={`${columns[id].title}正文`} className="min-w-0 overflow-y-auto overscroll-contain border-r border-border-subtle px-7 pb-24 pt-4 last:border-r-0 md:px-8">
            {blocks.map(block => {
              const first = block[0];
              const marked = block.some(row => row.key === readingKey);
              const column = columns[id];
              const inline = block.length > 1;
              return (
                <div key={first.key} data-reading-block={first.key} data-reading-mark={marked ? 'true' : undefined}
                  className={cn('group/reading relative mx-auto mb-4 max-w-[70ch] scroll-mt-6', marked && 'rounded-sm bg-primary-50/50 ring-1 ring-primary-200/60')}>
                  <button type="button" title={marked ? '看到这里' : '标记：看到这里'}
                    aria-label={`${column.title}：从这里继续阅读 — ${first.source.slice(0, 40)}`}
                    aria-pressed={marked} disabled={markBusy} onClick={() => onMark(first.key)}
                    className={cn('absolute -left-6 top-1 rounded p-1 text-text-muted transition-opacity hover:text-primary-700 focus:opacity-100 disabled:opacity-40 md:opacity-0 md:group-hover/reading:opacity-100', marked && 'text-primary-700 md:opacity-100')}>
                    <Bookmark className={cn('h-3.5 w-3.5', marked && 'fill-current')} />
                  </button>
                  {inline ? (
                    <div className={rowTextClass(first)}>{block.map((row, index) => (
                      <Fragment key={row.key}>{id === 'source' && index > 0 ? ' ' : null}<Cell row={row} column={column} inline /></Fragment>
                    ))}</div>
                  ) : <Cell row={first} column={column} />}
                </div>
              );
            })}
          </article>
        ))}
      </div>
    </div>
  );
}

function Cell({ row, column, inline = false }: { row: WorkbenchRow; column: PaneColumn; inline?: boolean }) {
  const textClass = rowTextClass(row);
  // 图片三栏都显示（译文里的图就是原文的图），也让三栏在图片处对齐
  if (row.kind === 'image') {
    return row.image ? <img src={row.image} alt="" loading="lazy" className="my-2 max-h-72 w-auto max-w-full rounded border border-border-subtle" /> : null;
  }
  if (!column.text) {
    if (inline) return <InlineMarkdown text={row.source} />;
    return (
      <div className={cn(textClass, row.kind === 'li' && 'pl-4 -indent-4 before:mr-2 before:content-["•"]')}>
        <InlineMarkdown text={row.source} />
      </div>
    );
  }
  const value = column.text(row);
  const other = column.adopt?.text(row);
  const editable = <EditableText
        id={`${column.id}:${row.key}`}
        value={value}
        placeholder={inline ? '待补译' : column.placeholder ?? ''}
        ariaLabel={`${column.title}：${row.source.slice(0, 40)}`}
        onSave={text => column.save!(row, text)}
        adopt={column.adopt && other ? { label: column.adopt.label, text: other } : null}
        className={inline ? (!value?.trim() ? 'mx-1 text-xs' : undefined) : 'min-w-0 flex-1'}
        inline={inline}
      />;
  if (inline) return editable;
  return (
    <div className={cn(textClass, row.kind === 'li' && 'flex gap-2 before:mt-1 before:content-["•"]')}>
      {editable}
    </div>
  );
}
