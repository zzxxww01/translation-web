import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { renderSlackSegments, renderSlackText } from './mrkdwn';
import type { SlackSegment } from './types';

/**
 * 按后端拆好的片段渲染 Slack 格式（mrkdwn / Markdown）。
 * 消息里的 HTML 一律转义，链接只认 http(s)/mailto，渲染结果再经 DOMPurify 消毒（见 mrkdwn.ts）。
 */
export function SlackText({ segments, className }: { segments: SlackSegment[]; className?: string }) {
  const html = useMemo(() => renderSlackSegments(segments), [segments]);
  return (
    <div
      className={cn('slack-md break-words text-[14px] leading-relaxed text-text-primary', className)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/** 一段纯文本（AI 中文、链接卡片正文、AI 摘要）按同样的格式渲染 */
export function SlackMarkdown({ text, className, lang }: { text: string; className?: string; lang?: string }) {
  const html = useMemo(() => renderSlackText(text), [text]);
  return <div lang={lang} className={cn('slack-md break-words', className)} dangerouslySetInnerHTML={{ __html: html }} />;
}
