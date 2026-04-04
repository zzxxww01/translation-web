/**
 * 导入参考译文模态框组件
 * 支持拖拽、粘贴和文件上传
 */

import { useState, useCallback, useRef } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button-extended';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { cn } from '@/shared/utils';

interface ImportVersionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (versionName: string, markdownContent: string) => Promise<void>;
  isImporting?: boolean;
}

export function ImportVersionModal({
  isOpen,
  onClose,
  onImport,
  isImporting = false,
}: ImportVersionModalProps) {
  const [versionName, setVersionName] = useState('');
  const [markdownContent, setMarkdownContent] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImport = useCallback(async () => {
    if (!versionName.trim() || !markdownContent.trim()) {
      return;
    }

    await onImport(versionName.trim(), markdownContent.trim());

    // Reset form
    setVersionName('');
    setMarkdownContent('');
  }, [versionName, markdownContent, onImport]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleFileUpload = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setMarkdownContent(content);
      // Auto-fill version name from filename if empty
      if (!versionName) {
        const name = file.name.replace(/\.[^/.]+$/, '');
        setVersionName(name);
      }
    };
    reader.readAsText(file);
  }, [versionName]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const file = e.dataTransfer.files[0];
        handleFileUpload(file);
      }
    },
    [handleFileUpload]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files[0]) {
        handleFileUpload(e.target.files[0]);
      }
    },
    [handleFileUpload]
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const pastedText = e.clipboardData.getData('text');
      if (pastedText && pastedText.length > 0) {
        setMarkdownContent(pastedText);
      }
    },
    []
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>导入参考译文</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* 版本名称 */}
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              版本名称
            </label>
            <Input
              value={versionName}
              onChange={(e) => setVersionName(e.target.value)}
              placeholder="例如：网友翻译v1.0"
            />
          </div>

          {/* Markdown内容 */}
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              Markdown内容
            </label>

            {/* 拖拽上传区域 */}
            <div
              className={cn(
                'relative mb-3 rounded-lg border-2 border-dashed p-6 text-center transition-colors',
                dragActive
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50',
                'cursor-pointer'
              )}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".md,.txt"
                onChange={handleFileInputChange}
                className="hidden"
              />
              <Upload className="mx-auto mb-2 h-10 w-10 text-muted-foreground" />
              <p className="text-sm font-medium text-foreground">
                拖拽文件到此处，或点击上传
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                支持 .md 和 .txt 格式
              </p>
            </div>

            {/* 或粘贴 */}
            <div className="mb-3 flex items-center gap-2">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">或直接粘贴内容</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            {/* 文本输入框 */}
            <Textarea
              value={markdownContent}
              onChange={(e) => setMarkdownContent(e.target.value)}
              onPaste={handlePaste}
              placeholder="粘贴参考译文的Markdown内容..."
              className="min-h-[200px] font-mono text-sm"
            />
          </div>

          {/* 预览 */}
          {markdownContent && (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium text-foreground">
                  内容预览
                </label>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setMarkdownContent('')}
                  leftIcon={<X className="h-3 w-3" />}
                >
                  清空
                </Button>
              </div>
              <div className="max-h-40 overflow-y-auto rounded-lg bg-muted p-3">
                <pre className="text-xs text-muted-foreground whitespace-pre-wrap">
                  {markdownContent.slice(0, 500)}
                  {markdownContent.length > 500 && '...'}
                </pre>
              </div>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-3 pt-4">
            <Button
              variant="outline"
              onClick={onClose}
              className="flex-1"
              disabled={isImporting}
            >
              取消
            </Button>
            <Button
              variant="default"
              onClick={handleImport}
              disabled={!versionName.trim() || !markdownContent.trim() || isImporting}
              isLoading={isImporting}
              leftIcon={<FileText className="h-4 w-4" />}
              className="flex-1"
            >
              {isImporting ? '导入中...' : '导入'}
            </Button>
          </div>

          {/* 提示信息 */}
          <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-950/30">
            <p className="text-xs text-blue-600 dark:text-blue-400">
              系统会自动将参考译文与原文段落对齐。如果某些段落无法自动对齐，您可以在导入后手动调整。
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
