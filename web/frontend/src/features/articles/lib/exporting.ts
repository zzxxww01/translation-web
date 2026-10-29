import { Marked } from 'marked';
import { sanitizeSourceHtml } from '@/shared/safeHtml';
import { wechatApi } from '@/features/wechat/api';
import { wechatPasteHtml, writeRichClipboard, type RichText } from '@/features/wechat/copy';
import { loadWechatDraft, saveWechatDraft } from '@/features/wechat/draft';

/**
 * 导出主译本的几种去处：下载 Markdown、打印成 PDF、复制全文、复制成公众号格式。
 * 都从同一份导出 Markdown（后端 /export）出发，和下载的文件一字不差。
 */

const marked = new Marked({ gfm: true, async: false });

/** 导出的 Markdown 渲染成干净的 HTML（图片保留，脚本和内联样式去掉） */
export function markdownToHtml(markdown: string): string {
  return sanitizeSourceHtml(marked.parse(markdown) as string);
}

/** 复制全文：粘进纯文本框是 Markdown，粘进文档编辑器是排好版的富文本 */
export function copyFullText(markdown: Promise<string>): Promise<void> {
  return writeRichClipboard(markdown.then(text => ({ text, html: markdownToHtml(text) })));
}

/** 复制成公众号格式：走微信排版页同一套接口（主题、图片处理沿用排版页上次的选择） */
export function copyForWechat(markdown: Promise<string>): Promise<void> {
  return writeRichClipboard(markdown.then(async (text): Promise<RichText> => {
    const draft = loadWechatDraft();
    const result = await wechatApi.format({
      markdown: text,
      theme: draft.selectedTheme,
      upload_images: draft.imageMode === 'upload',
      image_to_base64: draft.imageMode === 'base64',
    });
    return wechatPasteHtml(result.html, result.css);
  }));
}

/** 放进微信排版页的草稿里，换主题、看预览再复制 */
export function sendToWechatEditor(markdown: string): void {
  saveWechatDraft({ ...loadWechatDraft(), markdown });
}

const PRINT_CSS = `
@page { size: A4; margin: 18mm 17mm 20mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; color: #2b2730; font-family: "Noto Serif SC", "Source Serif 4", "Songti SC", "SimSun", serif;
  font-size: 11pt; line-height: 1.85; }
h1 { font-size: 20pt; line-height: 1.35; margin: 0 0 16pt; }
h2 { font-size: 14.5pt; line-height: 1.4; margin: 22pt 0 8pt; break-after: avoid; }
h3, h4 { font-size: 12pt; margin: 16pt 0 6pt; break-after: avoid; }
p { margin: 0 0 9pt; orphans: 2; widows: 2; }
img { display: block; max-width: 100%; max-height: 115mm; margin: 10pt auto 4pt; break-inside: avoid; }
em { font-style: normal; color: #574e57; }
blockquote { margin: 10pt 0; padding: 1pt 0 1pt 12pt; border-left: 2pt solid #ebc5d6; color: #574e57; }
pre, code { font-family: "JetBrains Mono", Consolas, "Courier New", monospace; font-size: 8.5pt; }
pre { white-space: pre-wrap; word-break: break-all; background: #f7f2f3; padding: 8pt 10pt; border-radius: 4pt; break-inside: avoid; }
a { color: #742a4f; text-decoration: none; }
ul, ol { margin: 0 0 9pt; padding-left: 18pt; }
li { margin-bottom: 3pt; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9.5pt; }
th, td { border: 0.5pt solid #e0d3d9; padding: 3pt 5pt; text-align: left; }
hr { border: 0; border-top: 0.5pt solid #e0d3d9; margin: 14pt 0; }
`;

/** 页面已经加载的字体（思源宋体等）原样给打印用的文档，PDF 和屏幕上同一套字 */
function pageFontFaces(): string {
  const rules: string[] = [];
  for (const sheet of Array.from(document.styleSheets)) {
    let list: CSSRuleList;
    try {
      list = sheet.cssRules;
    } catch {
      continue; // 跨域样式表读不到
    }
    for (const rule of Array.from(list)) {
      if (typeof CSSFontFaceRule !== 'undefined' && rule instanceof CSSFontFaceRule) rules.push(rule.cssText);
    }
  }
  return rules.join('\n');
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char]!);
}

/** 打印页的完整 HTML（单独导出便于测试） */
export function printDocument(markdown: string, title: string): string {
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>`
    + `<style>${pageFontFaces()}${PRINT_CSS}</style></head><body><article>${markdownToHtml(markdown)}</article></body></html>`;
}

/**
 * 导出 PDF：在隐藏的 iframe 里排好版，等图片和字体加载完，弹出浏览器的打印框（选「另存为 PDF」）。
 * 打印期间把页面标题换成文章标题，另存时默认文件名就是它。
 */
export async function printAsPdf(markdown: string, title: string): Promise<void> {
  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden', 'true');
  frame.tabIndex = -1;
  frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
  document.body.appendChild(frame);
  const view = frame.contentWindow;
  const doc = frame.contentDocument;
  if (!view || !doc) {
    frame.remove();
    throw new Error('浏览器不让打开打印页');
  }
  doc.open();
  doc.write(printDocument(markdown, title));
  doc.close();
  const images = Array.from(doc.images).filter(image => !image.complete)
    .map(image => new Promise(resolve => { image.onload = image.onerror = resolve; }));
  // 图片最多等 15 秒：个别图挂了也照样能打印
  await Promise.race([Promise.all([doc.fonts?.ready, ...images]), new Promise(resolve => setTimeout(resolve, 15_000))]);
  const previousTitle = document.title;
  let cleaned = false;
  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    document.title = previousTitle;
    frame.remove();
  };
  view.addEventListener('afterprint', () => setTimeout(cleanup, 0), { once: true });
  setTimeout(cleanup, 10 * 60_000); // 个别浏览器不发 afterprint
  document.title = title;
  view.focus();
  view.print();
}
