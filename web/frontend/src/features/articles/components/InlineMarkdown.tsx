import type { ReactNode } from 'react';

// [文字](链接)、**加粗**、*斜体*（图注常见「*来源：[…](…)*」，里面再套链接）
const INLINE = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|\*([^*\s][^*]*?)\*/g;

/** 段落里的 Markdown 链接、加粗、斜体渲染出来，其余原样；编辑时才显示原始写法。 */
export function InlineMarkdown({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(INLINE)) {
    const index = match.index ?? 0;
    if (index > last) parts.push(text.slice(last, index));
    if (match[1] !== undefined) {
      parts.push(
        <a
          key={index}
          href={match[2]}
          target="_blank"
          rel="noreferrer"
          onClick={event => event.stopPropagation()}
          className="text-primary-700 underline decoration-primary-200 underline-offset-2"
        >
          {match[1]}
        </a>
      );
    } else if (match[3] !== undefined) {
      parts.push(<strong key={index}><InlineMarkdown text={match[3]} /></strong>);
    } else {
      parts.push(<em key={index}><InlineMarkdown text={match[4]} /></em>);
    }
    last = index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}
