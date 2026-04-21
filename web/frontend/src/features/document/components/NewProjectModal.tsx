import { type FC, useCallback, useEffect, useRef, useState } from 'react';
import { FileText, Sparkles, Upload } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button-extended';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useCreateProject } from '../hooks';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated?: (projectId: string) => void;
}

const HTML_FILE_RE = /\.(html?|xhtml)$/i;
const MARKDOWN_FILE_RE = /\.(md|markdown)$/i;
const SOURCE_FILE_RE = /\.(html?|xhtml|md|markdown)$/i;

const isHtmlFile = (name: string) => HTML_FILE_RE.test(name);
const isMarkdownFile = (name: string) => MARKDOWN_FILE_RE.test(name);
const isSupportedSourceFile = (name: string) => SOURCE_FILE_RE.test(name);
const stripSourceExt = (name: string) => name.replace(SOURCE_FILE_RE, '');
const hasDraggedFiles = (dataTransfer?: DataTransfer | null) =>
  !!dataTransfer && Array.from(dataTransfer.types).includes('Files');

export const NewProjectModal: FC<NewProjectModalProps> = ({
  isOpen,
  onClose,
  onProjectCreated,
}) => {
  const [name, setName] = useState('');
  const [path, setPath] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [assets, setAssets] = useState<File[]>([]);
  const [assetsFolderName, setAssetsFolderName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isWindowDragging, setIsWindowDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const assetsInputRef = useRef<HTMLInputElement>(null);
  const windowDragDepthRef = useRef(0);

  const createMutation = useCreateProject();

  const currentFileIsHtml = !!file && isHtmlFile(file.name);
  const dropActive = isDragging || isWindowDragging;

  const resetAssets = useCallback(() => {
    setAssets([]);
    setAssetsFolderName('');
    if (assetsInputRef.current) {
      assetsInputRef.current.value = '';
    }
  }, []);

  const handleFileSelect = useCallback((selectedFile: File) => {
    if (!selectedFile) return;

    if (!isSupportedSourceFile(selectedFile.name)) {
      toast.error('请选择 HTML 或 Markdown 文件');
      return;
    }

    setFile(selectedFile);
    resetAssets();

    if (!name) {
      setName(stripSourceExt(selectedFile.name));
    }
  }, [name, resetAssets]);

  const handleDroppedFiles = useCallback((selectedFiles: FileList | null) => {
    const droppedFile = selectedFiles?.[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, [handleFileSelect]);

  const handleAssetsSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles || selectedFiles.length === 0) {
      resetAssets();
      return;
    }

    if (!file || !isHtmlFile(file.name)) {
      toast.error('只有 HTML 文件需要选择 *_files 资源目录');
      return;
    }

    const files = Array.from(selectedFiles);
    const first = files[0] as File & { webkitRelativePath?: string };
    const relativePath = first.webkitRelativePath || first.name;
    const topFolder = relativePath.split('/')[0];

    if (!topFolder.endsWith('_files') && !topFolder.endsWith('.files')) {
      toast.error('请选择对应的 *_files 资源目录');
      return;
    }

    const stem = stripSourceExt(file.name);
    if (!topFolder.startsWith(stem)) {
      toast.error('资源文件夹与 HTML 文件不匹配');
      return;
    }

    setAssets(files);
    setAssetsFolderName(topFolder);
  };

  const handleDragOver = (e: React.DragEvent) => {
    if (!hasDraggedFiles(e.dataTransfer)) return;
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    if (!hasDraggedFiles(e.dataTransfer)) return;
    e.preventDefault();
    setIsDragging(false);
    setIsWindowDragging(false);
    windowDragDepthRef.current = 0;
    handleDroppedFiles(e.dataTransfer.files);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleAssetsInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleAssetsSelect(e.target.files);
  };

  useEffect(() => {
    if (!isOpen) {
      queueMicrotask(() => {
        setIsDragging(false);
        setIsWindowDragging(false);
      });
      windowDragDepthRef.current = 0;
      return;
    }

    const handleWindowDragEnter = (e: DragEvent) => {
      if (!hasDraggedFiles(e.dataTransfer)) return;
      e.preventDefault();
      windowDragDepthRef.current += 1;
      setIsWindowDragging(true);
    };

    const handleWindowDragOver = (e: DragEvent) => {
      if (!hasDraggedFiles(e.dataTransfer)) return;
      e.preventDefault();
      setIsWindowDragging(true);
    };

    const handleWindowDragLeave = (e: DragEvent) => {
      if (!hasDraggedFiles(e.dataTransfer)) return;
      e.preventDefault();
      windowDragDepthRef.current = Math.max(windowDragDepthRef.current - 1, 0);
      if (windowDragDepthRef.current === 0) {
        setIsWindowDragging(false);
      }
    };

    const handleWindowDrop = (e: DragEvent) => {
      if (!hasDraggedFiles(e.dataTransfer)) return;
      e.preventDefault();
      windowDragDepthRef.current = 0;
      setIsWindowDragging(false);
      setIsDragging(false);
      handleDroppedFiles(e.dataTransfer?.files ?? null);
    };

    window.addEventListener('dragenter', handleWindowDragEnter);
    window.addEventListener('dragover', handleWindowDragOver);
    window.addEventListener('dragleave', handleWindowDragLeave);
    window.addEventListener('drop', handleWindowDrop);

    return () => {
      window.removeEventListener('dragenter', handleWindowDragEnter);
      window.removeEventListener('dragover', handleWindowDragOver);
      window.removeEventListener('dragleave', handleWindowDragLeave);
      window.removeEventListener('drop', handleWindowDrop);
      windowDragDepthRef.current = 0;
    };
  }, [handleDroppedFiles, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      toast.error('请输入项目名称');
      return;
    }

    if (!file && !path.trim()) {
      toast.error('请选择文件或输入路径');
      return;
    }

    try {
      let result;
      if (file) {
        const formData = new FormData();
        formData.append('name', name.trim());
        formData.append('file', file);

        if (currentFileIsHtml && assets.length > 0) {
          assets.forEach((asset) => {
            const relPath =
              (asset as File & { webkitRelativePath?: string }).webkitRelativePath ||
              asset.name;
            formData.append('assets', asset, relPath);
          });
        }

        result = await createMutation.mutateAsync(formData);
      } else {
        result = await createMutation.mutateAsync({
          name: name.trim(),
          html_path: path.trim(),
        });
      }

      handleClose();
      if (result?.id && onProjectCreated) {
        onProjectCreated(result.id);
      }
    } catch {
      // Error handled in mutation
    }
  };

  const handleClose = () => {
    if (!createMutation.isPending) {
      setName('');
      setPath('');
      setFile(null);
      setIsDragging(false);
      setIsWindowDragging(false);
      windowDragDepthRef.current = 0;
      resetAssets();
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) handleClose(); }}>
      <DialogContent className="sm:max-w-md">
        {isWindowDragging && (
          <div className="pointer-events-none fixed inset-0 z-[60] flex items-center justify-center">
            <div className="absolute inset-0 bg-primary/10 backdrop-blur-sm" />
            <div className="relative mx-6 flex w-full max-w-2xl flex-col items-center justify-center rounded-3xl border-2 border-dashed border-primary bg-background/92 px-8 py-14 text-center shadow-2xl">
              <Upload className="mb-4 h-14 w-14 text-primary" />
              <p className="text-xl font-semibold text-text-primary">
                释放文件即可创建项目
              </p>
              <p className="mt-2 text-sm text-text-muted">
                弹窗打开时，拖到浏览器任意位置都可以
              </p>
            </div>
          </div>
        )}
        <DialogHeader>
          <DialogTitle>新建项目</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="project-name">项目名称</Label>
            <Input
              id="project-name"
              placeholder="例如: apple-tsmc-analysis"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div>
            <Label className="mb-2 block">
              选择 HTML 或 Markdown 文件
            </Label>

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`
                relative flex cursor-pointer flex-col items-center justify-center
                rounded-lg border-2 border-dashed p-8 transition-all
                ${
                  dropActive
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50 hover:bg-bg-secondary'
                }
                ${file ? 'border-success bg-success/5' : ''}
              `}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".html,.htm,.md,.markdown,text/html,text/markdown,text/plain"
                onChange={handleFileInputChange}
                className="hidden"
              />

              {file ? (
                <>
                  <FileText className="mb-3 h-12 w-12 text-success" />
                  <p className="font-medium text-text-primary">{file.name}</p>
                  <p className="text-sm text-text-muted">{(file.size / 1024).toFixed(1)} KB</p>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      resetAssets();
                      if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                      }
                    }}
                    className="mt-3 text-sm text-primary hover:text-primary/80"
                  >
                    重新选择
                  </button>
                </>
              ) : (
                <>
                  <Upload className="mb-3 h-12 w-12 text-text-muted" />
                  <p className="font-medium text-text-primary">
                    {dropActive ? '释放文件' : '点击或拖拽 HTML/Markdown 文件到此处'}
                  </p>
                  <p className="mt-1 text-sm text-text-muted">支持 HTML 与 Markdown 格式</p>
                </>
              )}
            </div>
          </div>

          {currentFileIsHtml && (
            <div>
              <Label className="mb-2 block">
                选择对应 *_files 资源目录（可选）
              </Label>
              <div
                onClick={() => assetsInputRef.current?.click()}
                className={`
                  relative flex cursor-pointer flex-col items-center justify-center
                  rounded-lg border-2 border-dashed p-6 transition-all
                  ${
                    assets.length > 0
                      ? 'border-success bg-success/5'
                      : 'border-border hover:border-primary/50 hover:bg-bg-secondary'
                  }
                `}
              >
                <input
                  ref={assetsInputRef}
                  type="file"
                  multiple
                  // @ts-expect-error - webkitdirectory is supported by Chromium browsers
                  webkitdirectory=""
                  onChange={handleAssetsInputChange}
                  className="hidden"
                />

                {assets.length > 0 ? (
                  <>
                    <FileText className="mb-2 h-8 w-8 text-success" />
                    <p className="font-medium text-text-primary">
                      {assetsFolderName || '已选择资源目录'}
                    </p>
                    <p className="text-sm text-text-muted">{assets.length} 个文件</p>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        resetAssets();
                      }}
                      className="mt-2 text-sm text-primary hover:text-primary/80"
                    >
                      重新选择
                    </button>
                  </>
                ) : (
                  <>
                    <Upload className="mb-2 h-8 w-8 text-text-muted" />
                    <p className="font-medium text-text-primary">选择 *_files 目录</p>
                    <p className="mt-1 text-sm text-text-muted">用于 HTML 关联图片等资源</p>
                  </>
                )}
              </div>
            </div>
          )}

          {file && isMarkdownFile(file.name) && (
            <p className="text-sm text-text-muted">Markdown 文件无需选择 *_files 资源目录。</p>
          )}

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-bg-primary px-2 text-text-muted">或者使用路径</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="project-path">HTML/Markdown 文件路径</Label>
            <Input
              id="project-path"
              placeholder="例如: ./articles/article.html 或 ./articles/article.md"
              value={path}
              onChange={(e) => {
                setPath(e.target.value);
                setFile(null);
                resetAssets();
              }}
              disabled={!!file}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={createMutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" variant="default" isLoading={createMutation.isPending}>
              <Sparkles className="h-4 w-4" />
              创建项目
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
