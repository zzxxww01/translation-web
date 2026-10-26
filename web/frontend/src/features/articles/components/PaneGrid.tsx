import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode, type Ref } from 'react';
import { Bookmark, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { gridTemplate, PANES, type Collapsed } from '../lib/panes';
import { rowTextClass } from '../lib/rows';
import type { PaneId, WorkbenchRow } from '../types';
import { EditableText, type EditableTextHandle } from './EditableText';
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
  /** 整段采用或补齐缺译时的来源 */
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
  onMark: (key: string | null) => void;
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
          <article key={id} aria-label={`${columns[id].title}正文`} className="min-w-0 overflow-y-auto overscroll-contain border-r border-border-subtle px-7 pb-24 pt-6 last:border-r-0 md:px-8">
            {blocks.map(block => <ReadingBlock key={block[0].key} block={block} column={columns[id]}
              marked={block.some(row => row.key === readingKey)} markBusy={markBusy} onMark={onMark} />)}
          </article>
        ))}
      </div>
    </div>
  );
}

function ReadingBlock({ block, column, marked, markBusy, onMark }: {
  block: WorkbenchRow[];
  column: PaneColumn;
  marked: boolean;
  markBusy: boolean;
  onMark: (key: string | null) => void;
}) {
  const first = block[0];
  const inline = block.length > 1;
  const editors = useRef(new Map<string, EditableTextHandle>());
  const [protectedIds, setProtectedIds] = useState<Set<string>>(() => new Set());
  const [adopting, setAdopting] = useState(false);
  const registerEditor = useCallback((key: string, editor: EditableTextHandle | null) => {
    if (editor) editors.current.set(key, editor);
    else editors.current.delete(key);
  }, []);
  const onProtectionChange = useCallback((id: string, protectedDraft: boolean) => {
    setProtectedIds(current => {
      if (current.has(id) === protectedDraft) return current;
      const next = new Set(current);
      if (protectedDraft) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const comparison = column.adopt;
  const complete = Boolean(comparison && block.every(row => comparison.text(row)?.trim()));
  // 对照缺译时只补当前空白位置，绝不把不完整的对照覆盖到已有译文上。
  const candidates = comparison ? block.filter(row => {
    const other = comparison.text(row);
    return other?.trim() && (complete ? other !== column.text?.(row) : !column.text?.(row)?.trim());
  }) : [];
  const canFill = !complete && candidates.length > 0;
  const protectedDraft = protectedIds.size > 0;
  const unavailable = adopting || protectedDraft || candidates.length === 0;
  const showAdopt = comparison && first.kind !== 'image' && (!complete || candidates.length > 0);
  const adoptTitle = protectedDraft ? '请先完成本段编辑并保存，再采用另一版译文'
    : !complete && !canFill ? '对照译文尚未完整，暂时不能采用整段'
    : canFill ? '只补齐本段尚无译文的位置，保留已有译文'
    : '采用这一原文段落的全部对照译文';
  const adoptBlock = async () => {
    if (unavailable || [...editors.current.values()].some(editor => editor.isProtected())) return;
    setAdopting(true);
    try {
      await Promise.all(candidates.map(row => editors.current.get(row.key)?.adopt(comparison!.text(row)!)));
    } finally {
      setAdopting(false);
    }
  };
  const cell = (row: WorkbenchRow) => <Cell row={row} column={column} inline={inline}
    editorRef={editor => registerEditor(row.key, editor)} onProtectionChange={onProtectionChange} />;

  return (
    <div data-reading-block={first.key} data-reading-mark={marked ? 'true' : undefined}
      className={cn('group/reading relative mx-auto mb-5 max-w-[70ch] scroll-mt-8', marked && 'rounded-sm bg-primary-50/50 ring-1 ring-primary-200/60')}>
      <div data-reading-actions className="pointer-events-none absolute -top-3 right-0 z-10 flex max-w-full -translate-y-1/2 items-center gap-1 text-[11px] leading-5">
        <button type="button" title={marked ? '取消“看到这里”' : '标记：看到这里'}
          aria-label={`${column.title}：从这里继续阅读 — ${first.source.slice(0, 40)}`}
          aria-pressed={marked} disabled={markBusy} onClick={() => onMark(marked ? null : first.key)}
          className={cn('pointer-events-auto flex shrink-0 items-center gap-1 rounded-md border border-border-subtle bg-white px-2 py-0.5 text-text-muted shadow-sm transition-opacity hover:border-primary-200 hover:text-primary-700 disabled:opacity-40 [@media(hover:hover)]:opacity-0 group-hover/reading:opacity-100 group-focus-within/reading:opacity-100', marked && 'border-primary-200 text-primary-700 [@media(hover:hover)]:opacity-100')}>
          <Bookmark className={cn('h-3 w-3', marked && 'fill-current')} />看到这里
        </button>
        {showAdopt && <button type="button" title={adoptTitle} disabled={unavailable}
          onMouseDown={event => event.preventDefault()} onClick={() => void adoptBlock()}
          className="pointer-events-auto min-w-0 truncate rounded-md border border-border-subtle bg-white px-2 py-0.5 text-text-secondary shadow-sm transition-opacity hover:border-primary-200 hover:text-primary-700 disabled:cursor-default disabled:text-text-disabled [@media(hover:hover)]:opacity-0 group-hover/reading:opacity-100 group-focus-within/reading:opacity-100">
          {adopting ? '正在采用…' : canFill ? `用 ${comparison.label} 补齐本段` : `采用 ${comparison.label} 整段`}
        </button>}
      </div>
      {inline ? <div className={rowTextClass(first)}>{block.map((row, index) => (
        <Fragment key={row.key}>{column.id === 'source' && index > 0 ? ' ' : null}{cell(row)}</Fragment>
      ))}</div> : cell(first)}
    </div>
  );
}

function Cell({ row, column, inline = false, editorRef, onProtectionChange }: {
  row: WorkbenchRow;
  column: PaneColumn;
  inline?: boolean;
  editorRef?: Ref<EditableTextHandle>;
  onProtectionChange?: (id: string, protectedDraft: boolean) => void;
}) {
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
  const editable = <EditableText
        ref={editorRef}
        id={`${column.id}:${row.key}`}
        value={value}
        placeholder={inline ? '待补译' : column.placeholder ?? ''}
        ariaLabel={`${column.title}：${row.source.slice(0, 40)}`}
        onSave={text => column.save!(row, text)}
        onProtectionChange={onProtectionChange}
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
