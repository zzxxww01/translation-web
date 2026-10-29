import { Fragment, useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode, type Ref, type RefObject } from 'react';
import { ChevronLeft, ChevronRight, Flag } from 'lucide-react';
import { cn } from '@/lib/utils';
import { gridTemplate, PANES, type Collapsed } from '../lib/panes';
import { rowTextClass } from '../lib/rows';
import type { PaneId, WorkbenchRow } from '../types';
import { EditableText, type EditableTextHandle } from './EditableText';
import { InlineMarkdown } from './InlineMarkdown';
import type { Tone } from '../lib/versions';
import { TONE_DOT } from '../lib/tones';
import { FOCUS_RING, MEASURE, STROKE } from '../lib/ui';
import { IconAction, VersionHeader, type VersionHeaderProps } from './VersionHeader';

export interface PaneColumn {
  id: PaneId;
  /** 竖条上的栏名 */
  title: string;
  /** 栏头三行；「收起」按钮由这里加在操作最后 */
  header: VersionHeaderProps;
  /** 中文栏：取这一行的译文、保存；英文栏不填 */
  text?: (row: WorkbenchRow) => string | null;
  save?: (row: WorkbenchRow, text: string) => Promise<void>;
  placeholder?: string;
  /** 整段采用或补齐缺译时的来源 */
  adopt?: { label: string; text: (row: WorkbenchRow) => string | null };
  /** 主译本栏：极浅暖底 + 栏头顶部梅红细线 */
  primary?: boolean;
  /** 这一版只读（重翻中、还没出译文） */
  readOnly?: boolean;
  /** 收起竖条上的状态圆点 */
  tone?: Tone;
  /** 换了版本时整栏重新挂载，编辑框不会带着上一版的草稿 */
  versionKey?: string;
  /** 同一版的内容整篇换过（重新翻译导入后）就变；变了才淡入，切标签不淡入 */
  contentKey?: string;
  /** 有它就显示它，不显示段落（对照栏没有别的版本时） */
  empty?: ReactNode;
}

interface PaneGridProps {
  rows: WorkbenchRow[];
  columns: Record<PaneId, PaneColumn>;
  collapsed: Collapsed;
  onToggle: (pane: PaneId) => void;
  /** 手机上一次只显示一栏 */
  mobilePane: PaneId | null;
  readingMark?: { key: string; at: string } | null;
  markBusy: boolean;
  onMark: (key: string | null) => void;
  jump: number;
  /** 放在最右边那一栏栏头最后的按钮（沉浸模式的退出） */
  corner?: ReactNode;
}

/** 收起竖条、栏头、正文三处共用的分隔线 */
const DIVIDER = 'border-r border-border-subtle last:border-r-0';

function fadeIn(element: Element | null | undefined) {
  if (!(element instanceof HTMLElement) || typeof element.animate !== 'function') return;
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
  element.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: 'ease-out' });
}

type FadeKeys = Record<'main' | 'compare', [version: string | undefined, content: string | undefined]>;

/**
 * 动效只有两处（设计文档 5.4）：对调主译本时两栏交叉淡入；同一版内容整篇换过（重翻导入）时这一栏淡入。
 * 切对照标签、切手机上的栏、第一次打开都不动。在绘制前开始动画，新内容不会先整块闪一下。
 */
function useVersionFade(container: RefObject<HTMLDivElement | null>, keys: FadeKeys) {
  const seen = useRef<FadeKeys | null>(null);
  const [mainVersion, mainContent] = keys.main;
  const [compareVersion, compareContent] = keys.compare;
  useLayoutEffect(() => {
    const now: FadeKeys = { main: [mainVersion, mainContent], compare: [compareVersion, compareContent] };
    const before = seen.current;
    seen.current = now;
    if (!before) return;
    const swapped = before.main[0] !== now.main[0];
    for (const pane of ['main', 'compare'] as const) {
      const replaced = before[pane][0] === now[pane][0] && before[pane][1] !== now[pane][1];
      if (swapped || replaced) fadeIn(container.current?.querySelector(`[data-pane-body="${pane}"]`));
    }
  }, [container, mainVersion, mainContent, compareVersion, compareContent]);
}

/** 「继续阅读」后标记那一段停在离栏顶这么远（上面那行「上次读到这里」也露出来） */
const MARK_GAP = 24;
/** 落位后这么久之内，标记上方晚加载的图片把它推走了就再拉回来 */
const FOLLOW_MS = 6000;

function alignToMark(root: HTMLElement, smooth: boolean) {
  // 每一栏自己滚：不用 scrollIntoView（它会连外层一起滚，几栏同时平滑滚动时还可能只滚动最后一栏）
  root.querySelectorAll<HTMLElement>('[data-pane-body]').forEach(pane => {
    const block = pane.querySelector<HTMLElement>('[data-reading-mark="true"]');
    if (!block) return;
    const top = pane.scrollTop + block.getBoundingClientRect().top - pane.getBoundingClientRect().top - MARK_GAP;
    pane.scrollTo({ top: Math.max(0, top), behavior: smooth ? 'smooth' : 'auto' });
  });
}

/**
 * 三栏都滚到阅读标记处。图片没写尺寸、懒加载，滚到之后标记上方的图才加载出来，会把标记往下推几百像素：
 * 平滑滚动结束时、之后每加载完一张图，再对齐一次；你自己滚动、按键或点击就不再管。返回清理函数。
 */
function followMark(root: HTMLElement): () => void {
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  alignToMark(root, !reduce);
  let settled = false;
  const realign = () => { if (settled) alignToMark(root, false); };
  const onLoad = (event: Event) => { if (event.target instanceof HTMLImageElement) realign(); };
  const timers = [
    setTimeout(() => { settled = true; realign(); }, reduce ? 0 : 700), // 平滑滚动中途不打断
    setTimeout(() => stop(), FOLLOW_MS),
  ];
  const userInput = ['wheel', 'touchstart', 'pointerdown'] as const;
  function stop() {
    timers.forEach(clearTimeout);
    root.removeEventListener('load', onLoad, true);
    userInput.forEach(type => root.removeEventListener(type, stop, true));
    window.removeEventListener('keydown', stop, true);
  }
  root.addEventListener('load', onLoad, true); // 图片的 load 不冒泡，用捕获
  userInput.forEach(type => root.addEventListener(type, stop, { capture: true, passive: true }));
  window.addEventListener('keydown', stop, true);
  return stop;
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

export function PaneGrid({ rows, columns, collapsed, onToggle, mobilePane, readingMark, markBusy, onMark, jump, corner }: PaneGridProps) {
  const visible = mobilePane ? [mobilePane] : PANES;
  const template = mobilePane ? 'minmax(0, 1fr)' : gridTemplate(collapsed);
  const isCollapsed = (id: PaneId) => !mobilePane && collapsed[id];
  const lastOpen = visible.filter(id => !isCollapsed(id)).at(-1);
  const container = useRef<HTMLDivElement>(null);
  const lastJump = useRef(0);
  useEffect(() => {
    if (jump === lastJump.current || !container.current) return;
    lastJump.current = jump;
    return followMark(container.current);
  }, [jump]);
  const blocks = readingBlocks(rows);
  useVersionFade(container, {
    main: [columns.main.versionKey, columns.main.contentKey],
    compare: [columns.compare.versionKey, columns.compare.contentKey],
  });

  // 栏头格子和正文都留出滚动条的位置（scrollbar-gutter），两边内容宽度一样，版心才上下对齐
  return (
    // 三栏直接铺满顶栏以下（方案 A）：不再留页边、画纸张阴影
    <div ref={container} className="flex min-h-0 flex-1 flex-col overflow-hidden" data-testid="pane-grid">
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-bg-secondary">
        <div className="z-20 grid shrink-0 border-b border-border-subtle bg-bg-secondary" style={{ gridTemplateColumns: template }}>
          {visible.map(id => (
            <div key={id} data-pane={id} className={cn('relative min-w-0', DIVIDER,
              isCollapsed(id) ? 'bg-bg-tertiary' : columns[id].primary && 'bg-paper-primary before:absolute before:inset-x-0 before:top-0 before:h-0.5 before:bg-gradient-to-r before:from-primary-300 before:to-primary-500')}>
              {isCollapsed(id) ? (
                <button type="button" onClick={() => onToggle(id)} aria-label={`展开${columns[id].title}`} title="展开这一栏"
                  className={cn('flex h-full min-h-12 w-full items-center justify-center gap-1.5 text-text-muted transition-colors hover:text-primary-700', FOCUS_RING, 'focus-visible:-outline-offset-2')}>
                  <ChevronRight aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
                  {columns[id].tone && <span aria-hidden className={cn('h-1.5 w-1.5 rounded-full', TONE_DOT[columns[id].tone!])} />}
                </button>
              ) : (
                <div className={cn('flex items-center overflow-hidden px-4 [scrollbar-gutter:stable] md:px-[30px]', mobilePane ? 'py-2' : 'h-12')}>
                  <VersionHeader {...columns[id].header} stacked={Boolean(mobilePane)} collapse={<>
                    {!mobilePane && (
                      <IconAction label={`收起${columns[id].title}`} title="收起这一栏" onClick={() => onToggle(id)}>
                        <ChevronLeft aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
                      </IconAction>
                    )}
                    {id === lastOpen && corner}
                  </>} />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="grid min-h-0 flex-1" style={{ gridTemplateColumns: template }}>
          {visible.map(id => isCollapsed(id) ? (
            <div key={id} className={cn('bg-bg-tertiary', DIVIDER)}>
              <span className="block pt-1 text-center text-[12px] tracking-[0.3em] text-text-muted [writing-mode:vertical-rl]">{columns[id].title}</span>
            </div>
          ) : (
            <article key={`${id}:${columns[id].versionKey ?? ''}`} id={`pane-${id}`} data-pane-body={id} aria-label={`${columns[id].title}正文`}
              className={cn('min-w-0 overflow-y-auto overscroll-contain px-4 pb-24 pt-5 [scrollbar-gutter:stable] md:px-[30px]', DIVIDER,
                // 第一段若是章节标题，不再叠它自己的上边距：和栏头的距离与栏头内边距一致
                '[&>[data-reading-block]:first-child>:last-child]:pt-0',
                columns[id].primary && 'bg-paper-primary')}>
              {columns[id].empty ?? blocks.map(block => <ReadingBlock key={block[0].key} block={block} column={columns[id]}
                marked={block.some(row => row.key === readingMark?.key) ? markedAt(readingMark?.at) : null} markBusy={markBusy} onMark={onMark} />)}
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * 段落上边缘的小工具条按钮：悬停或聚焦这一段时才出现。没出现时也点不到——
 * 以前透明的「采用整段」就压在两段之间，点空白处会把整段换掉。
 */
const TOOL = `rounded-md border border-border-subtle bg-bg-secondary px-2 py-0.5 shadow-thumb transition-opacity hover:border-primary-200 hover:text-primary-700 disabled:opacity-40 [@media(hover:hover)]:opacity-0 group-hover/reading:opacity-100 group-focus-within/reading:opacity-100 ${FOCUS_RING}`;

const markClock = new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });

/** 阅读标记的时间写成「10-29 21:40」；读不出时间时只写「上次读到这里」 */
function markedAt(at: string | undefined): string {
  const time = at ? new Date(at) : null;
  if (!time || Number.isNaN(time.getTime())) return '上次读到这里';
  const parts = Object.fromEntries(markClock.formatToParts(time).map(part => [part.type, part.value]));
  return `上次读到这里 · ${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
}

function ReadingBlock({ block, column, marked: markLabel, markBusy, onMark }: {
  block: WorkbenchRow[];
  column: PaneColumn;
  /** 标记在这一段时是那行小字（「上次读到这里 · 时间」），否则 null */
  marked: string | null;
  markBusy: boolean;
  onMark: (key: string | null) => void;
}) {
  const first = block[0];
  const inline = block.length > 1;
  const marked = markLabel !== null;
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
  const showAdopt = comparison && !column.readOnly && first.kind !== 'image' && (!complete || candidates.length > 0);
  const adoptTitle = protectedDraft ? '请先完成本段编辑并保存，再采用另一版译文'
    : !complete && !canFill ? '对照译文尚未完整，暂时不能采用整段'
    : canFill ? '只补齐本段尚无译文的位置，保留已有译文'
    : '采用这一原文段落的全部对照译文';
  const adoptBlock = async () => {
    if (unavailable || [...editors.current.values()].some(editor => editor.isProtected())) return;
    setAdopting(true);
    try {
      const group = `adopt:${first.key}:${Date.now()}`; // 一次采用改的几个片段，撤销时一起撤回
      await Promise.all(candidates.map(row => editors.current.get(row.key)?.adopt(comparison!.text(row)!, group)));
    } finally {
      setAdopting(false);
    }
  };
  const cell = (row: WorkbenchRow) => <Cell row={row} column={column} inline={inline}
    editorRef={editor => registerEditor(row.key, editor)} onProtectionChange={onProtectionChange} />;

  return (
    <div data-reading-block={first.key} data-rows={block.map(row => row.key).join(' ')} data-reading-mark={marked ? 'true' : undefined}
      className={cn(MEASURE, 'group/reading relative isolate mb-5 scroll-mt-8',
        // 悬停底纹比文字四周各宽一点，不贴着字的边
        'after:pointer-events-none after:absolute after:-inset-x-2.5 after:-inset-y-1 after:-z-10 after:rounded-lg after:bg-paper-hover after:opacity-0 after:transition-opacity [@media(hover:hover)]:hover:after:opacity-100',
        // 阅读标记：页边一道梅红细线，和悬停底纹之间留出空隙
        marked && 'before:absolute before:-left-3 before:bottom-1 before:top-1 before:w-0.5 before:rounded-full before:bg-primary-500 md:before:-left-4')}>
      {/* 工具条下沿压住段落顶边 1px：鼠标从段落往上移到按钮，悬停不会中途断掉 */}
      <div data-reading-actions className="absolute -top-3 right-0 z-10 flex max-w-full -translate-y-1/2 items-center gap-1 text-[11px] leading-5 [@media(hover:hover)]:pointer-events-none group-hover/reading:pointer-events-auto group-focus-within/reading:pointer-events-auto">
        <button type="button" title={marked ? '取消阅读标记' : '下次从这里接着读'}
          aria-label={`${column.title}：${marked ? '取消标记' : '标记读到这里'} — ${first.source.slice(0, 40)}`}
          aria-pressed={marked} disabled={markBusy} onClick={() => onMark(marked ? null : first.key)}
          className={cn(TOOL, 'flex shrink-0 items-center gap-1 text-text-muted', marked && 'pointer-events-auto border-primary-200 text-primary-700')}>
          <Flag aria-hidden className={cn('h-3 w-3', marked && 'fill-current')} strokeWidth={STROKE} />{marked ? '取消标记' : '标记读到这里'}
        </button>
        {showAdopt && <button type="button" title={adoptTitle} disabled={unavailable}
          onMouseDown={event => event.preventDefault()} onClick={() => void adoptBlock()}
          className={cn(TOOL, 'min-w-0 truncate text-text-secondary disabled:cursor-default disabled:text-text-disabled')}>
          {adopting ? '正在采用…' : canFill ? `用 ${comparison.label} 补齐本段` : `采用 ${comparison.label} 整段`}
        </button>}
      </div>
      {markLabel && <p className="mb-0.5 text-[11px] font-medium leading-5 text-primary-500">{markLabel}</p>}
      {inline ? <div className={rowTextClass(first, column.id === 'source' ? 'en' : 'zh')}>{block.map((row, index) => (
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
  const textClass = rowTextClass(row, column.id === 'source' ? 'en' : 'zh');
  // 图片三栏都显示（译文里的图就是原文的图），也让三栏在图片处对齐
  if (row.kind === 'image') {
    return row.image ? <img src={row.image} alt="" loading="lazy" className="my-2 max-h-72 w-auto max-w-full rounded-md border border-border-subtle" /> : null;
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
        historyKey={`${column.versionKey ?? column.id}@${column.contentKey ?? ''}:${row.key}`}
        value={value}
        placeholder={inline ? '待补译' : column.placeholder ?? ''}
        ariaLabel={`${column.title}：${row.source.slice(0, 40)}`}
        onSave={text => column.save!(row, text)}
        onProtectionChange={onProtectionChange}
        className={inline ? (!value?.trim() ? 'mx-1 text-xs' : undefined) : 'min-w-0 flex-1'}
        inline={inline}
        readOnly={column.readOnly}
      />;
  if (inline) return editable;
  return (
    <div className={cn(textClass, row.kind === 'li' && 'flex gap-2 before:mt-1 before:content-["•"]')}>
      {editable}
    </div>
  );
}
