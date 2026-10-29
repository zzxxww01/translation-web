/**
 * 排版结果 → 能直接粘进公众号编辑器的富文本，以及写进剪贴板。微信排版页和文章工作台共用。
 */

export interface RichText {
  html: string;
  text: string;
}

/**
 * 后端给的 html + css：公式渲染成 SVG（rendered 是已经渲染好的，就不再渲染），样式全部内联
 * （公众号会剥掉 <style>；CSS 变量后端已解析成字面值）。
 */
export async function wechatPasteHtml(rawHtml: string, css: string, rendered?: string): Promise<RichText> {
  let html = rendered ?? rawHtml;
  if (!rendered && rawHtml.includes('data-latex')) {
    const { renderFormulas } = await import('./formulaRenderer');
    html = (await renderFormulas(rawHtml)).html;
  }
  const { default: juice } = await import('juice');
  const processed = juice(`<style>${css}</style>${html}`, { inlinePseudoElements: true, preserveImportant: true });
  const container = document.createElement('div');
  container.innerHTML = processed;
  return { html: processed, text: container.textContent || '' };
}

/**
 * 富文本写进剪贴板。content 可以是还没准备好的 Promise：要在点击的那一刻就调用这里，
 * 浏览器才认这是用户操作（准备内容要先请求接口、渲染公式，耗时可能好几秒）。
 */
export async function writeRichClipboard(content: RichText | Promise<RichText>): Promise<void> {
  const ready = Promise.resolve(content);
  if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
    await navigator.clipboard.write([
      new ClipboardItem({
        'text/html': ready.then(({ html }) => new Blob([html], { type: 'text/html' })),
        'text/plain': ready.then(({ text }) => new Blob([text], { type: 'text/plain' })),
      }),
    ]);
    return;
  }
  const { html } = await ready;
  const container = document.createElement('div');
  container.innerHTML = html;
  container.style.position = 'fixed';
  container.style.left = '-9999px';
  document.body.appendChild(container);
  const range = document.createRange();
  range.selectNodeContents(container);
  const selection = window.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
  const success = document.execCommand('copy');
  selection?.removeAllRanges();
  document.body.removeChild(container);
  if (!success) throw new Error('Copy command failed');
}
