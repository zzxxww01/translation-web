import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { useFormatWechat, useWechatThemes } from './hooks';
import juice from 'juice';
import {
  Copy,
  Eye,
  FileText,
  ImagePlus,
  Palette,
  UploadCloud,
  WandSparkles,
} from 'lucide-react';
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
  const themes = useMemo(() => themesData?.themes || [], [themesData]);

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
    <div className="flex h-full min-h-0 flex-1 flex-col gap-3 overflow-hidden bg-[linear-gradient(180deg,#f8fafc_0%,#eef6f3_46%,#f8fafc_100%)] p-3 md:gap-4 md:p-6">
      <div className="relative shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-white/95 p-4 shadow-sm">
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50 text-slate-800">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                WeChat Studio
              </p>
              <h1 className="text-xl font-semibold leading-tight text-slate-950 md:text-2xl">
                微信公众号排版
              </h1>
            </div>
          </div>

          <div className="grid gap-2 lg:flex lg:flex-wrap lg:items-center lg:gap-3">
            <label className="flex min-w-0 items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-sm shadow-inner shadow-white/70">
              <span className="flex shrink-0 items-center gap-2 font-medium text-slate-600">
                <Palette className="h-4 w-4 text-teal-700" />
                主题
              </span>
              <select
                value={selectedTheme}
                onChange={(e) => setSelectedTheme(e.target.value)}
                className="h-10 min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-3 text-right text-sm font-semibold text-slate-950 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15 lg:flex-none lg:text-left"
              >
                {themes.map((theme) => (
                  <option key={theme.id} value={theme.id}>
                    {theme.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="group flex min-w-0 cursor-pointer items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white/90 px-3 py-2.5 text-sm shadow-sm transition">
              <input
                type="checkbox"
                checked={uploadImages}
                onChange={(e) => setUploadImages(e.target.checked)}
                className="peer sr-only"
              />
              <span className="flex min-w-0 items-center gap-2 font-medium text-slate-700">
                <UploadCloud className="h-4 w-4 text-blue-700" />
                <span className="truncate">上传图片到图床</span>
              </span>
              <span className="relative h-6 w-11 shrink-0 rounded-full bg-slate-200 transition after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition peer-checked:bg-primary peer-checked:after:translate-x-5" />
            </label>
            <label className="group flex min-w-0 cursor-pointer items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white/90 px-3 py-2.5 text-sm shadow-sm transition">
              <input
                type="checkbox"
                checked={imageToBase64}
                onChange={(e) => setImageToBase64(e.target.checked)}
                className="peer sr-only"
              />
              <span className="flex min-w-0 items-center gap-2 font-medium text-slate-700">
                <ImagePlus className="h-4 w-4 text-amber-600" />
                <span className="truncate">图片转Base64</span>
              </span>
              <span className="relative h-6 w-11 shrink-0 rounded-full bg-slate-200 transition after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition peer-checked:bg-primary peer-checked:after:translate-x-5" />
            </label>
            <div className="hidden items-center gap-3 lg:flex">
              <Button onClick={handleConvert} disabled={isPending}>
                {isPending ? '转换中...' : '转换'}
              </Button>
              <Button onClick={handleCopy} disabled={!html} variant="outline">
                复制
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-auto lg:grid-cols-2 lg:overflow-hidden">
        {/* 左侧：Markdown 输入 */}
        <div className="flex min-h-[calc(100dvh-280px)] flex-col overflow-hidden rounded-lg border border-slate-200/90 bg-white shadow-[0_18px_50px_-36px_rgba(15,23,42,0.55)] lg:h-full lg:min-h-0">
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50/90 px-4">
            <span className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <FileText className="h-4 w-4 text-blue-700" />
              Markdown
            </span>
            <span className="rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white">
              输入
            </span>
          </div>
          <Textarea
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            placeholder="在此输入 Markdown 内容..."
            className="min-h-0 flex-1 resize-none border-0 bg-white/95 p-4 font-mono text-[15px] leading-7 shadow-none"
          />
        </div>

        {/* 右侧：预览区（使用iframe隔离） */}
        <div className="flex min-h-[calc(100dvh-280px)] flex-col overflow-hidden rounded-lg border border-slate-200/90 bg-white shadow-[0_18px_50px_-36px_rgba(15,23,42,0.55)] lg:h-full lg:min-h-0">
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50/90 px-4">
            <span className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Eye className="h-4 w-4 text-teal-700" />
              预览
            </span>
            <span className="rounded-full bg-teal-700 px-2.5 py-1 text-[11px] font-medium text-white">
              微信
            </span>
          </div>
          {html ? (
            <iframe
              ref={iframeRef}
              className="h-full w-full border-0"
              title="微信预览"
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-8 text-center text-sm text-slate-500">
              <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-400 shadow-sm">
                <Eye className="h-6 w-6" />
              </div>
              <span className="font-medium">等待预览</span>
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 rounded-lg border border-slate-200 bg-white/95 p-2 shadow-[0_-18px_50px_-34px_rgba(15,23,42,0.55)] lg:hidden">
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <Button onClick={handleConvert} disabled={isPending} className="h-12 rounded-lg shadow-[0_14px_26px_-18px_rgba(29,78,216,0.9)]">
            <WandSparkles className="h-4 w-4" />
            {isPending ? '转换中...' : '转换'}
          </Button>
          <Button onClick={handleCopy} disabled={!html} variant="outline" className="h-12 w-28 rounded-lg border-slate-200 bg-white">
            <Copy className="h-4 w-4" />
            复制
          </Button>
        </div>
      </div>
    </div>
  );
}
