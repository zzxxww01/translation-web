import { useEffect, useMemo, useState } from 'react';
import {
  Check,
  Clipboard,
  Eye,
  FileText,
  Image,
  Loader2,
  Settings2,
  WandSparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { loadWechatDraft, saveWechatDraft } from './draft';
import { useFormatWechat, useWechatThemes } from './hooks';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';
import type { WechatImageMode } from './types';
import './wechat.css';

type WorkspaceView = 'editor' | 'preview';

const imageModes: Array<{
  id: WechatImageMode;
  title: string;
  description: string;
}> = [
  {
    id: 'keep',
    title: '保留原链接',
    description: '不处理图片地址，转换速度最快。',
  },
  {
    id: 'upload',
    title: '上传到图床',
    description: '将远程图片上传后替换为新地址。',
  },
  {
    id: 'base64',
    title: '转为 Base64',
    description: '把图片直接嵌入 HTML，内容体积会增大。',
  },
];

function ImageModeOptions({
  value,
  onChange,
}: {
  value: WechatImageMode;
  onChange: (mode: WechatImageMode) => void;
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 text-sm font-medium">图片处理</legend>
      {imageModes.map(mode => (
        <label
          key={mode.id}
          className={cn(
            'flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors',
            value === mode.id ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50'
          )}
        >
          <input
            type="radio"
            name="wechat-image-mode"
            value={mode.id}
            checked={value === mode.id}
            onChange={() => onChange(mode.id)}
            className="mt-1"
          />
          <span className="min-w-0">
            <span className="flex items-center gap-2 text-sm font-medium">
              {value === mode.id ? <Check className="h-3.5 w-3.5 text-primary" /> : null}
              {mode.title}
            </span>
            <span className="mt-1 block text-xs leading-5 text-muted-foreground">
              {mode.description}
            </span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}

export function WechatFeature() {
  const initialDraft = useMemo(loadWechatDraft, []);
  const [markdown, setMarkdown] = useState(initialDraft.markdown);
  const [selectedTheme, setSelectedTheme] = useState(initialDraft.selectedTheme);
  const [imageMode, setImageMode] = useState<WechatImageMode>(initialDraft.imageMode);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('editor');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const formatWechat = useFormatWechat();
  const {
    data: themesData,
    isError: themesFailed,
    error: themesError,
  } = useWechatThemes();
  const { handleError } = useErrorHandler();

  const html = formatWechat.data?.html || '';
  const css = formatWechat.data?.css || '';
  const themes = useMemo(() => themesData?.themes || [], [themesData]);
  const selectedThemeName =
    themes.find(theme => theme.id === selectedTheme)?.name || selectedTheme;
  const imageModeName = imageModes.find(mode => mode.id === imageMode)?.title || '保留原链接';
  useEffect(() => {
    if (themesFailed) handleError(themesError, '主题列表加载失败');
  }, [handleError, themesError, themesFailed]);

  const previewDocument = html
    ? `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body style="margin:0;padding:20px;background:white">${html}</body></html>`
    : '';

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      saveWechatDraft({ markdown, selectedTheme, imageMode });
    }, 250);
    return () => window.clearTimeout(timeoutId);
  }, [imageMode, markdown, selectedTheme]);

  useEffect(() => {
    if (!themes.length || themes.some(theme => theme.id === selectedTheme)) return;
    setSelectedTheme(themes[0].id);
  }, [selectedTheme, themes]);

  const handleConvert = () => {
    if (!markdown.trim()) {
      toast.error('请输入 Markdown 内容');
      return;
    }

    formatWechat.mutate(
      {
        markdown,
        theme: selectedTheme,
        upload_images: imageMode === 'upload',
        image_to_base64: imageMode === 'base64',
      },
      {
        onSuccess: () => {
          setWorkspaceView('preview');
          toast.success('排版转换完成');
        },
      }
    );
  };

  const handleCopy = async () => {
    if (!html || !css) {
      toast.error('请先转换 Markdown');
      return;
    }

    try {
      const { default: juice } = await import('juice');
      const styledHtml = `<style>${css}</style>${html}`;
      const inlinedHtml = juice(styledHtml, {
        inlinePseudoElements: true,
        preserveImportant: true,
      });
      const processedHtml = inlinedHtml
        .replace(/hsl\(var\(--foreground\)\)/g, '#3f3f3f')
        .replace(/var\(--blockquote-background\)/g, '#f7f7f7')
        .replace(/var\(--md-primary-color\)/g, '#3b82f6');

      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = processedHtml;
      const plainText = tempDiv.textContent || '';

      if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
        await navigator.clipboard.write([
          new ClipboardItem({
            'text/html': new Blob([processedHtml], { type: 'text/html' }),
            'text/plain': new Blob([plainText], { type: 'text/plain' }),
          }),
        ]);
      } else {
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
        if (!success) throw new Error('Copy command failed');
      }

      toast.success('已复制，可直接粘贴到微信编辑器');
    } catch {
      toast.error('复制失败，请手动复制预览内容');
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold sm:text-xl">微信公众号排版</h1>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {selectedThemeName} · {imageModeName}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={() => setSettingsOpen(true)}
          aria-label="打开排版设置"
          title="排版设置"
        >
          <Settings2 className="h-4 w-4" />
        </Button>
      </header>

      <div className="flex shrink-0 border-b p-2 lg:hidden" role="tablist" aria-label="排版工作区">
        <button
          type="button"
          role="tab"
          aria-selected={workspaceView === 'editor'}
          onClick={() => setWorkspaceView('editor')}
          className={cn(
            'flex h-9 flex-1 items-center justify-center gap-2 rounded-md text-sm font-medium',
            workspaceView === 'editor' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
          )}
        >
          <FileText className="h-4 w-4" />
          编辑
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={workspaceView === 'preview'}
          onClick={() => setWorkspaceView('preview')}
          className={cn(
            'flex h-9 flex-1 items-center justify-center gap-2 rounded-md text-sm font-medium',
            workspaceView === 'preview' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
          )}
        >
          <Eye className="h-4 w-4" />
          预览
        </button>
      </div>

      <main className="grid min-h-0 flex-1 lg:grid-cols-2">
        <section
          className={cn(
            'min-h-0 border-r bg-background p-3 sm:p-4',
            workspaceView !== 'editor' && 'hidden lg:block'
          )}
          role="tabpanel"
          aria-label="Markdown 编辑"
        >
          <Textarea
            value={markdown}
            onChange={event => setMarkdown(event.target.value)}
            placeholder="在此输入 Markdown 内容..."
            aria-label="Markdown 内容"
            className="h-full min-h-[360px] resize-none border-0 bg-transparent p-2 font-mono text-sm shadow-none focus-visible:ring-0"
          />
        </section>

        <section
          className={cn(
            'min-h-0 bg-white',
            workspaceView !== 'preview' && 'hidden lg:block'
          )}
          role="tabpanel"
          aria-label="微信排版预览"
        >
          {html ? (
            <iframe
              className="h-full min-h-[420px] w-full border-0"
              title="微信排版预览"
              sandbox="allow-same-origin"
              srcDoc={previewDocument}
            />
          ) : (
            <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 px-6 text-center text-sm text-muted-foreground">
              <Image className="h-8 w-8" aria-hidden="true" />
              <p>转换后的内容将在这里显示</p>
            </div>
          )}
        </section>
      </main>

      <footer className="sticky bottom-0 z-10 flex shrink-0 items-center gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur sm:justify-end sm:px-6">
        <Button
          type="button"
          onClick={handleConvert}
          disabled={formatWechat.isPending || !markdown.trim()}
          className="flex-1 sm:flex-none"
        >
          {formatWechat.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <WandSparkles className="h-4 w-4" />
          )}
          {formatWechat.isPending ? '转换中' : '转换'}
        </Button>
        <Button
          type="button"
          onClick={() => void handleCopy()}
          disabled={!html || formatWechat.isPending}
          variant="outline"
          className="flex-1 sm:flex-none"
        >
          <Clipboard className="h-4 w-4" />
          复制
        </Button>
      </footer>

      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-h-[90dvh] max-w-md overflow-y-auto">
          <DialogHeader>
            <DialogTitle>排版设置</DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            <label className="block space-y-2 text-sm font-medium">
              <span>排版主题</span>
              <select
                value={selectedTheme}
                onChange={event => setSelectedTheme(event.target.value)}
                className="h-10 w-full rounded-md border bg-background px-3 text-foreground"
                disabled={themesFailed}
              >
                {themes.map(theme => (
                  <option key={theme.id} value={theme.id}>
                    {theme.name}
                  </option>
                ))}
                {!themes.length ? <option value={selectedTheme}>{selectedTheme}</option> : null}
              </select>
              {themesFailed ? (
                <span className="block text-xs text-destructive">主题列表加载失败，仍可使用当前主题。</span>
              ) : null}
            </label>
            <ImageModeOptions value={imageMode} onChange={setImageMode} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
