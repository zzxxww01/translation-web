import DOMPurify from 'dompurify';
import { Marked } from 'marked';
import { emojify } from './lib';
import type { SlackSegment } from './types';
import './mrkdwn.css';

/**
 * Slack 消息的格式渲染：Slack 的 mrkdwn（*粗* _斜_ ~删~ `码` ```块``` > 引用 • 列表），
 * 也兼容别人直接贴进来的 Markdown（**粗**、- 列表、1. 列表）。
 * 做法：链接 / 提及先换成占位符，把 mrkdwn 改写成 Markdown，再交给 marked，最后 DOMPurify 消毒。
 * 消息原文里的 < > & 一律转义，所以消息里写的 HTML 只会原样显示，不会生效。
 */

const marked = new Marked({ gfm: true, breaks: true, async: false });
marked.use({
  renderer: {
    link({ href, tokens }) {
      const text = this.parser.parseInline(tokens);
      if (!/^(https?:|mailto:)/i.test(href)) return text;
      return `<a href="${escapeAttr(href)}" target="_blank" rel="noreferrer noopener">${text}</a>`;
    },
  },
});

// 链接 / 提及的占位符：Unicode 私用区字符，正常消息里不会出现
const OPEN = '\uE000';
const CLOSE = '\uE001';
const PLACEHOLDER_RE = new RegExp(`${OPEN}(\\d+)${CLOSE}`, 'g');
// ```代码块``` 和 `行内代码` 里的内容不做任何改写
const CODE_RE = /(```[\s\S]*?```|`[^`\n]+`)/;

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeAttr(text: string): string {
  return escapeHtml(text).replace(/"/g, '&quot;');
}

function escapeLinkLabel(text: string): string {
  return escapeHtml(text).replace(/([\\[\]*_~`])/g, '\\$1');
}

function linkTarget(url: string): string {
  // 括号不配对会截断 Markdown 链接；encodeURIComponent 不编码括号，手动换
  return url.replace(/[ ()<>]/g, ch => ({ ' ': '%20', '(': '%28', ')': '%29', '<': '%3C', '>': '%3E' })[ch] ?? ch);
}

/** mrkdwn 的行内 / 行首记号改写成 Markdown；输入已经转义过 HTML。 */
function mrkdwnToMarkdown(text: string): string {
  return text
    // *粗体* → **粗体**（已经是 **粗体** 的不动）
    .replace(/(^|[^\w*\\])\*(?=\S)([^*\n]*?\S)\*(?![\w*])/g, '$1**$2**')
    // ~删除线~ → ~~删除线~~
    .replace(/(^|[^\w~\\])~(?=\S)([^~\n]*?\S)~(?![\w~])/g, '$1~~$2~~')
    // 行首的 • ◦ ▪ 列表 → Markdown 列表
    .replace(/^([ \t]*)[•◦▪][ \t]+/gm, '$1- ')
    // 行首的 > 引用（Slack 里是 &gt;，这里已经转义过）
    .replace(/^&gt;[ \t]?/gm, '> ');
}

function codeToMarkdown(code: string, plain: (s: string) => string): string {
  const text = plain(code);
  if (!text.startsWith('```')) return text;
  const inner = text.slice(3, -3).replace(/^\n/, '').replace(/\n$/, '');
  const fence = inner.includes('```') ? '~~~~' : '```';
  return `\n\n${fence}\n${inner}\n${fence}\n\n`;
}

export function segmentsToMarkdown(segments: SlackSegment[]): string {
  const tokens: SlackSegment[] = [];
  const joined = segments.map(seg => {
    if (seg.type === 'text') return emojify(seg.text);
    tokens.push(seg);
    return `${OPEN}${tokens.length - 1}${CLOSE}`;
  }).join('');

  // 代码里的占位符换回纯文字；代码外的换成 Markdown 链接 / 提及标签
  const plain = (s: string) => s.replace(PLACEHOLDER_RE, (_, i: string) => tokens[Number(i)]?.text ?? '');
  const rich = (s: string) => s.replace(PLACEHOLDER_RE, (_, i: string) => {
    const seg = tokens[Number(i)];
    if (!seg) return '';
    if (seg.type === 'mention') return `<span class="slack-mention">${escapeHtml(seg.text)}</span>`;
    if (seg.type === 'link' && /^(https?:|mailto:)/i.test(seg.url)) return `[${escapeLinkLabel(seg.text)}](${linkTarget(seg.url)})`;
    return escapeHtml(seg.text);
  });

  return joined
    .split(CODE_RE)
    .map((part, i) => (i % 2 === 1 ? codeToMarkdown(part, plain) : rich(mrkdwnToMarkdown(escapeHtml(part)))))
    .join('');
}

export function renderSlackSegments(segments: SlackSegment[]): string {
  const html = marked.parse(segmentsToMarkdown(segments)) as string;
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'del', 's', 'code', 'pre', 'blockquote', 'ul', 'ol', 'li', 'a', 'span',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
    // 链接协议已在 link 渲染器里只放行 http(s)/mailto；这里不设 ALLOWED_URI_REGEXP，它会把 target 等属性值也当 URI 校验删掉
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'start'],
  });
}

/** 纯文本（AI 中文、链接卡片正文）也按 mrkdwn 渲染 */
export function renderSlackText(text: string): string {
  return renderSlackSegments([{ type: 'text', text }]);
}

/** 列表预览用：去掉格式记号，只留文字 */
export function stripMrkdwn(text: string): string {
  return text
    .replace(/```/g, '')
    .replace(/`([^`\n]+)`/g, '$1')
    .replace(/\*\*([^*\n]+)\*\*/g, '$1')
    .replace(/(^|[^\w*])\*([^*\n]+)\*(?![\w*])/g, '$1$2')
    .replace(/(^|[^\w~])~~?([^~\n]+)~~?(?![\w~])/g, '$1$2')
    .replace(/(^|[^\w])_([^_\n]+)_(?![\w])/g, '$1$2')
    .replace(/^[ \t]*>[ \t]?/gm, '')
    .replace(/^([ \t]*)[•◦▪*-][ \t]+/gm, '$1• ')
    .replace(/^#{1,6}[ \t]+/gm, '');
}
