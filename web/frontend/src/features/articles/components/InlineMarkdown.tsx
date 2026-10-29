import type { ReactNode } from 'react';
import { parseInline, type InlineNode } from '../lib/inline';

function render(nodes: InlineNode[]): ReactNode[] {
  return nodes.map((node, index) => {
    if ('children' in node) {
      const Tag = node.kind;
      return <Tag key={index}>{render(node.children)}</Tag>;
    }
    if (node.kind === 'text') return node.text;
    return (
      <a
        key={index}
        href={node.href}
        target="_blank"
        rel="noreferrer"
        onClick={event => event.stopPropagation()}
        className="text-primary-700 underline decoration-primary-200 underline-offset-2"
      >
        {node.text}
      </a>
    );
  });
}

/** 段落里的 Markdown 链接、加粗、斜体渲染出来，其余原样；编辑时才显示原始写法。 */
export function InlineMarkdown({ text }: { text: string }) {
  return <>{render(parseInline(text))}</>;
}
