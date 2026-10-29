// [文字](链接)、**加粗**、*斜体*（图注常见「*来源：[…](…)*」，里面再套链接）
const INLINE = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|\*([^*\s][^*]*?)\*/g;

/** 一段看得见的文字；at 是它在原始 Markdown 里的起点，点击位置据此换算回原文 */
export interface InlineText {
  kind: 'text' | 'link';
  text: string;
  at: number;
  href?: string;
}

export interface InlineGroup {
  kind: 'strong' | 'em';
  children: InlineNode[];
}

export type InlineNode = InlineText | InlineGroup;

export function parseInline(text: string, base = 0): InlineNode[] {
  const nodes: InlineNode[] = [];
  let last = 0;
  for (const match of text.matchAll(INLINE)) {
    const index = match.index ?? 0;
    if (index > last) nodes.push({ kind: 'text', text: text.slice(last, index), at: base + last });
    if (match[1] !== undefined) nodes.push({ kind: 'link', text: match[1], href: match[2], at: base + index + 1 });
    else if (match[3] !== undefined) nodes.push({ kind: 'strong', children: parseInline(match[3], base + index + 2) });
    else nodes.push({ kind: 'em', children: parseInline(match[4], base + index + 1) });
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

/** 排版后第 offset 个字的位置，换算成原始 Markdown 里的位置 */
export function renderedToRaw(text: string, offset: number): number {
  let seen = 0;
  for (const piece of visible(parseInline(text))) {
    if (offset <= seen + piece.text.length) return piece.at + offset - seen;
    seen += piece.text.length;
  }
  return text.length;
}
