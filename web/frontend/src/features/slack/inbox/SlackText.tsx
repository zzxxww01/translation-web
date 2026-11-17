import { emojify } from './lib';
import type { SlackSegment } from './types';

/** 按后端拆好的片段渲染，不拼 HTML：链接只认 http(s)/mailto，其余都当纯文本。 */
export function SlackText({ segments }: { segments: SlackSegment[] }) {
  return (
    <div className="whitespace-pre-wrap break-words text-[14px] leading-relaxed text-text-primary">
      {segments.map((seg, i) => {
        if (seg.type === 'mention') {
          return (
            <span key={i} className="rounded bg-primary-50 px-0.5 font-medium text-primary-700">
              {seg.text}
            </span>
          );
        }
        if (seg.type === 'link' && /^(https?:|mailto:)/.test(seg.url)) {
          return (
            <a key={i} href={seg.url} target="_blank" rel="noreferrer noopener" className="break-all text-primary-700 underline-offset-2 hover:underline">
              {seg.text}
            </a>
          );
        }
        // Slack 的 *粗体*：只认同一行内成对的星号
        return (
          <span key={i}>
            {emojify(seg.text).split(/(\*[^*\n]+\*)/).map((part, j) =>
              part.length > 2 && part.startsWith('*') && part.endsWith('*')
                ? <strong key={j} className="font-semibold">{part.slice(1, -1)}</strong>
                : part
            )}
          </span>
        );
      })}
    </div>
  );
}
