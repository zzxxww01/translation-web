// [文字](链接)、**加粗**、*斜体*（图注常见「*来源：[…](…)*」，里面再套链接）
const INLINE = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|\*([^*\s][^*]*?)\*/g;

/** 一段看得见的文字；at 是它在原始 Markdown 里的起点，点击位置据此换算回原文 */
export interface InlineText {
  kind: 'text' | 'link';
  text: string;
  at: number;
  href?: string;
  /** 链接整段写法在原文里的范围 [起, 止) */
  raw?: [number, number];
}

export interface InlineGroup {
  kind: 'strong' | 'em';
  children: InlineNode[];
  raw: [number, number];
}

export type InlineNode = InlineText | InlineGroup;

export function parseInline(text: string, base = 0): InlineNode[] {
  const nodes: InlineNode[] = [];
  let last = 0;
  for (const match of text.matchAll(INLINE)) {
    const index = match.index ?? 0;
    const raw: [number, number] = [base + index, base + index + match[0].length];
    if (index > last) nodes.push({ kind: 'text', text: text.slice(last, index), at: base + last });
    if (match[1] !== undefined) nodes.push({ kind: 'link', text: match[1], href: match[2], at: base + index + 1, raw });
    else if (match[3] !== undefined) nodes.push({ kind: 'strong', children: parseInline(match[3], base + index + 2), raw });
    else nodes.push({ kind: 'em', children: parseInline(match[4], base + index + 1), raw });
    last = index + match[0].length;
  }
  if (last < text.length) nodes.push({ kind: 'text', text: text.slice(last), at: base + last });
  return nodes;
}

function visible(nodes: InlineNode[]): InlineText[] {
  return nodes.flatMap(node => ('children' in node ? visible(node.children) : [node]));
}

/** 有没有会被渲染掉的写法：没有的话排版视图和编辑框里的字一模一样 */
export function hasInlineMarkup(text: string): boolean {
  return parseInline(text).some(node => node.kind !== 'text');
}

/**
 * 排版后第 offset 个字的位置，换算成原始 Markdown 里的位置。
 * 正好落在两段的交界处时：left 算前一段的末尾，right 算后一段的开头。
 */
function toRaw(text: string, offset: number, bias: 'left' | 'right'): number {
  let seen = 0;
  for (const piece of visible(parseInline(text))) {
    const end = seen + piece.text.length;
    if (bias === 'left' ? offset <= end : offset < end) return piece.at + offset - seen;
    seen = end;
  }
  return text.length;
}

export function renderedToRaw(text: string, offset: number): number {
  return toRaw(text, offset, 'left');
}

/** 链接、加粗、斜体：整段写法的范围、去掉记号后的范围、排版后占的位置 */
interface Markup {
  raw: [number, number];
  inner: [number, number];
  shown: [number, number];
}

function markups(text: string): Markup[] {
  const found: Markup[] = [];
  let shown = 0;
  const walk = (nodes: InlineNode[]) => {
    for (const node of nodes) {
      if ('children' in node) {
        const from = shown;
        walk(node.children);
        const mark = node.kind === 'strong' ? 2 : 1;
        found.push({ raw: node.raw, inner: [node.raw[0] + mark, node.raw[1] - mark], shown: [from, shown] });
        continue;
      }
      if (node.kind === 'link' && node.raw) found.push({ raw: node.raw, inner: [node.at, node.at + node.text.length], shown: [shown, shown + node.text.length] });
      shown += node.text.length;
    }
  };
  walk(parseInline(text));
  return found;
}

/**
 * 排版视图里选中的 [start, end)，换算成原始 Markdown 里要替换的范围（选中后直接粘贴、打字时用）。
 * - 选区在一个链接（或加粗、斜体）里面：只换里面的字，格式保留；
 * - 选区把整个链接都盖住了：连同写法一起换掉；
 * - 选区只盖住链接的一部分：先把这个链接去掉格式变成普通文字（字都留着），再换。返回的 text 就是去掉格式后的原文。
 */
export function rawSelection(text: string, start: number, end: number): { text: string; start: number; end: number } {
  if (start === end) {
    const at = renderedToRaw(text, start);
    return { text, start: at, end: at };
  }
  let current = text;
  for (;;) {
    const marks = markups(current);
    const partial = marks.find(({ shown: [from, to] }) => start < to && end > from
      && !(start >= from && end <= to) && !(start <= from && end >= to));
    if (partial) {
      current = current.slice(0, partial.raw[0]) + current.slice(partial.inner[0], partial.inner[1]) + current.slice(partial.raw[1]);
      continue;
    }
    let rawStart = toRaw(current, start, 'right');
    let rawEnd = toRaw(current, end, 'left');
    for (const { raw, shown: [from, to] } of marks) {
      if (start <= from && end >= to && (start < from || end > to)) {
        rawStart = Math.min(rawStart, raw[0]);
        rawEnd = Math.max(rawEnd, raw[1]);
      }
    }
    return { text: current, start: rawStart, end: rawEnd };
  }
}
