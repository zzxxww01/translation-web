import DOMPurify from 'dompurify';
import { Marked } from 'marked';

const marked = new Marked({ gfm: true, breaks: true, async: false });

/** Claude 的回复是 Markdown（术语表、稿件都在里面），渲染后必须消毒再进 DOM：
 * 回复里可能原样引用了网页源码。 */
export function renderMarkdown(text: string): string {
  const html = marked.parse(text) as string;
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'form', 'input', 'button', 'textarea', 'select', 'iframe', 'video', 'audio', 'img'],
    FORBID_ATTR: ['style', 'srcset', 'formaction', 'autofocus'],
    ALLOW_DATA_ATTR: false,
  });
}
