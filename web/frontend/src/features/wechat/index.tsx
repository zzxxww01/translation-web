import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { useFormatWechat, useWechatThemes } from './hooks';
import juice from 'juice';
import './wechat.css';

export function WechatFeature() {
  const [markdown, setMarkdown] = useState('');
  const [selectedTheme, setSelectedTheme] = useState('default');
  const [uploadImages, setUploadImages] = useState(false);
  const [imageToBase64, setImageToBase64] = useState(false);
  const { mutate: formatWechat, isPending, data } = useFormatWechat();
  const { data: themesData } = useWechatThemes();
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const html = data?.html || '';
  const css = data?.css || '';
  const themes = themesData?.themes || [];

  // 调试信息
  useEffect(() => {
    console.log('themesData:', themesData);
    console.log('themes:', themes);
  }, [themesData, themes]);

  // 更新iframe内容
  useEffect(() => {
    if (iframeRef.current && html && css) {
      const iframeDoc = iframeRef.current.contentDocument;
      if (iframeDoc) {
        iframeDoc.open();
        iframeDoc.write(`
          <!DOCTYPE html>
          <html>
          <head>
            <meta charset="utf-8">
            <style>${css}</style>
          </head>
          <body style="margin: 0; padding: 20px; background: white;">
            ${html}
          </body>
          </html>
        `);
        iframeDoc.close();
      }
    }
  }, [html, css]);

  const handleConvert = () => {
    if (!markdown.trim()) {
      toast.error('请输入 Markdown 内容');
      return;
    }
    formatWechat({
      markdown,
      theme: selectedTheme,
      upload_images: uploadImages,
      image_to_base64: imageToBase64,
    });
  };

  const handleCopy = async () => {
    if (!html || !css) {
      toast.error('请先转换 Markdown');
      return;
    }

    try {
      // 使用juice将CSS内联化
      const styledHtml = `<style>${css}</style>${html}`;
      const inlinedHtml = juice(styledHtml, {
        inlinePseudoElements: true,
        preserveImportant: true,
      });

      // 替换CSS变量为实际值（参考doocs-md）
      const processedHtml = inlinedHtml
        .replace(/hsl\(var\(--foreground\)\)/g, '#3f3f3f')
        .replace(/var\(--blockquote-background\)/g, '#f7f7f7')
        .replace(/var\(--md-primary-color\)/g, '#3b82f6');

      // 获取纯文本
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = processedHtml;
      const plainText = tempDiv.textContent || '';

      // 方法1: 使用 ClipboardItem API
      if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
        const clipboardItem = new ClipboardItem({
          'text/html': new Blob([processedHtml], { type: 'text/html' }),
          'text/plain': new Blob([plainText], { type: 'text/plain' }),
        });
        await navigator.clipboard.write([clipboardItem]);
        toast.success('已复制到剪贴板，可直接粘贴到微信编辑器');
        return;
      }

      // 方法2: 降级到 execCommand
      const container = document.createElement('div');
      container.innerHTML = processedHtml;
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

      if (success) {
        toast.success('已复制到剪贴板，可直接粘贴到微信编辑器');
      } else {
        throw new Error('execCommand 失败');
      }
    } catch (error) {
      console.error('复制失败:', error);
      toast.error('复制失败，请手动复制预览区内容');
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">微信公众号排版</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <span>主题:</span>
            <select
              value={selectedTheme}
              onChange={(e) => setSelectedTheme(e.target.value)}
              className="rounded border px-2 py-1 text-sm"
            >
              {themes.map((theme) => (
                <option key={theme.id} value={theme.id}>
                  {theme.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={uploadImages}
              onChange={(e) => setUploadImages(e.target.checked)}
              className="rounded"
            />
            上传图片到图床
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={imageToBase64}
              onChange={(e) => setImageToBase64(e.target.checked)}
              className="rounded"
            />
            图片转Base64
          </label>
          <Button onClick={handleConvert} disabled={isPending}>
            {isPending ? '转换中...' : '转换'}
          </Button>
          <Button onClick={handleCopy} disabled={!html} variant="outline">
            复制
          </Button>
        </div>
      </div>

      <div className="grid flex-1 grid-cols-2 gap-4 overflow-hidden">
        {/* 左侧：Markdown 输入 */}
        <div className="flex flex-col overflow-hidden rounded-lg border">
          <Textarea
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            placeholder="在此输入 Markdown 内容..."
            className="flex-1 resize-none border-0 font-mono text-sm"
          />
        </div>

        {/* 右侧：预览区（使用iframe隔离） */}
        <div className="flex flex-col overflow-hidden rounded-lg border bg-white">
          {html ? (
            <iframe
              ref={iframeRef}
              className="h-full w-full border-0"
              title="微信预览"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-400">
              转换后的内容将在这里显示
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
