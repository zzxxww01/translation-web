import { useState } from 'react';
import { toast } from 'sonner';
import { useFormatWechat, useWechatThemes } from './hooks';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Copy, FileText, Sparkles } from 'lucide-react';

export function WechatFeature() {
  const [markdown, setMarkdown] = useState('');
  const [html, setHtml] = useState('');
  const [theme, setTheme] = useState('default');
  const [imageMode, setImageMode] = useState<'keep' | 'base64'>('keep');

  const formatMutation = useFormatWechat();
  const { data: themesData } = useWechatThemes();

  const handleFormat = async () => {
    if (!markdown.trim()) {
      toast.error('请输入 Markdown 内容');
      return;
    }

    try {
      const result = await formatMutation.mutateAsync({
        markdown,
        theme,
        upload_images: false,
        image_to_base64: imageMode === 'base64',
      });

      setHtml(result.html);
      toast.success(`转换成功！${result.image_count > 0 ? `处理了 ${result.image_count} 张图片` : ''}`);
    } catch (error) {
      console.error('格式化失败:', error);
      toast.error('格式化失败，请检查 Markdown 格式');
    }
  };

  const handleCopy = async () => {
    if (!html) {
      toast.error('请先转换 Markdown');
      return;
    }

    try {
      const blob = new Blob([html], { type: 'text/html' });
      const clipboardItem = new ClipboardItem({ 'text/html': blob });
      await navigator.clipboard.write([clipboardItem]);
      toast.success('已复制到剪贴板，可直接粘贴到微信编辑器');
    } catch (error) {
      console.error('复制失败:', error);
      toast.error('复制失败，请手动复制预览区内容');
    }
  };

  const handleClear = () => {
    setMarkdown('');
    setHtml('');
  };

  return (
    <div className="flex h-full flex-col gap-4 p-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-green-500 to-emerald-600">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">微信排版</h1>
            <p className="text-sm text-muted-foreground">Markdown 转微信公众号格式</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Select value={theme} onValueChange={setTheme}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="选择主题" />
            </SelectTrigger>
            <SelectContent>
              {themesData?.themes.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={imageMode} onValueChange={(v) => setImageMode(v as 'keep' | 'base64')}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="keep">保持原链接</SelectItem>
              <SelectItem value="base64">转 Base64</SelectItem>
            </SelectContent>
          </Select>

          <Button onClick={handleFormat} disabled={formatMutation.isPending}>
            <Sparkles className="mr-2 h-4 w-4" />
            {formatMutation.isPending ? '转换中...' : '转换'}
          </Button>

          <Button onClick={handleCopy} variant="outline" disabled={!html}>
            <Copy className="mr-2 h-4 w-4" />
            复制
          </Button>

          <Button onClick={handleClear} variant="ghost">
            清空
          </Button>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="grid flex-1 grid-cols-2 gap-4 overflow-hidden">
        {/* 左侧：Markdown 输入 */}
        <div className="flex flex-col gap-2 overflow-hidden rounded-lg border bg-card">
          <div className="border-b px-4 py-2">
            <h3 className="text-sm font-medium text-foreground">Markdown 输入</h3>
          </div>
          <Textarea
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            placeholder="粘贴或输入 Markdown 内容..."
            className="flex-1 resize-none border-0 font-mono text-sm focus-visible:ring-0"
          />
        </div>

        {/* 右侧：预览区 */}
        <div className="flex flex-col gap-2 overflow-hidden rounded-lg border bg-card">
          <div className="border-b px-4 py-2">
            <h3 className="text-sm font-medium text-foreground">预览</h3>
          </div>
          <div className="flex-1 overflow-auto p-4">
            {html ? (
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                转换后的内容将在这里显示
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
