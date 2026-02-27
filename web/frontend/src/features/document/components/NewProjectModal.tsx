import { type FC, useState, useRef } from 'react';
import { Sparkles, Upload, FileText } from 'lucide-react';
import { Button } from '../../../components/ui';
import { Input } from '../../../components/ui';
import { Modal } from '../../../components/ui';
import { useCreateProject } from '../hooks';
import { useToast } from '../../../components/ui';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated?: (projectId: string) => void;
}

export const NewProjectModal: FC<NewProjectModalProps> = ({ isOpen, onClose, onProjectCreated }) => {
  const [name, setName] = useState('');
  const [path, setPath] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [assets, setAssets] = useState<File[]>([]);
  const [assetsFolderName, setAssetsFolderName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const assetsInputRef = useRef<HTMLInputElement>(null);
  const createMutation = useCreateProject();
  const { showError } = useToast();

  const handleFileSelect = (selectedFile: File) => {
    if (!selectedFile) return;

    if (!selectedFile.type.includes('html') && !selectedFile.name.endsWith('.html')) {
      showError('请选择HTML文件');
      return;
    }

    setFile(selectedFile);
    setAssets([]);
    setAssetsFolderName('');

    const fileName = selectedFile.name.replace(/\.html$/i, '');
    if (!name) {
      setName(fileName);
    }
  };

  const handleAssetsSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setAssets([]);
      setAssetsFolderName('');
      return;
    }

    const files = Array.from(selectedFiles);
    const first = files[0] as File & { webkitRelativePath?: string };
    const relativePath = first.webkitRelativePath || first.name;
    const topFolder = relativePath.split('/')[0];

    if (!topFolder.endsWith('_files') && !topFolder.endsWith('.files')) {
      showError('请选择对应的 *_files 资源目录');
      return;
    }

    if (file) {
      const stem = file.name.replace(/\.html$/i, '');
      if (!topFolder.startsWith(stem)) {
        showError('资源文件夹与HTML文件不匹配');
        return;
      }
    }

    setAssets(files);
    setAssetsFolderName(topFolder);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      showError('请输入项目名称');
      return;
    }

    if (!file && !path.trim()) {
      showError('请选择文件或输入路径');
      return;
    }

    try {
      let result;
      if (file) {
        const formData = new FormData();
        formData.append('name', name.trim());
        formData.append('file', file);
        if (assets.length > 0) {
          assets.forEach(asset => {
            const relPath = (asset as File & { webkitRelativePath?: string }).webkitRelativePath || asset.name;
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
      setAssets([]);
      setAssetsFolderName('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      if (assetsInputRef.current) {
        assetsInputRef.current.value = '';
      }
      onClose();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="新建项目" size="md">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* 项目名称 */}
        <Input
          label="项目名称"
          placeholder="例如: apple-tsmc-analysis"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        {/* 文件方式 */}
        <div>
          <label className="mb-2 block text-sm font-medium text-text-primary">
            选择HTML文件
          </label>

          {/* 拖拽区域 */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative flex cursor-pointer flex-col items-center justify-center
              rounded-lg border-2 border-dashed p-8 transition-all
              ${isDragging
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50 hover:bg-bg-secondary'
              }
              ${file ? 'border-success bg-success/5' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".html,text/html"
              onChange={handleFileInputChange}
              className="hidden"
            />

            {file ? (
              <>
                <FileText className="mb-3 h-12 w-12 text-success" />
                <p className="font-medium text-text-primary">{file.name}</p>
                <p className="text-sm text-text-muted">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
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
                  {isDragging ? '释放文件' : '点击或拖拽HTML文件到此处'}
                </p>
                <p className="mt-1 text-sm text-text-muted">支持HTML格式</p>
              </>
            )}
          </div>
        </div>

        {/* 资源目录选择 */}
        <div>
          <label className="mb-2 block text-sm font-medium text-text-primary">
            选择对应*_files资源目录
          </label>
          <div
            onClick={() => assetsInputRef.current?.click()}
            className={`
              relative flex cursor-pointer flex-col items-center justify-center
              rounded-lg border-2 border-dashed p-6 transition-all
              ${assets.length > 0 ? 'border-success bg-success/5' : 'border-border hover:border-primary/50 hover:bg-bg-secondary'}
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
                    setAssets([]);
                    setAssetsFolderName('');
                    if (assetsInputRef.current) {
                      assetsInputRef.current.value = '';
                    }
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
                <p className="mt-1 text-sm text-text-muted">包含网页相关资源文件</p>
              </>
            )}
          </div>
        </div>

        {/* 或者使用路径 */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-bg-primary px-2 text-text-muted">或者使用路径</span>
          </div>
        </div>

        <Input
          label="HTML 文件路径"
          placeholder="例如: ./articles/article.html"
          value={path}
          onChange={(e) => {
            setPath(e.target.value);
            setFile(null);
          }}
          disabled={!!file}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={createMutation.isPending}
          >
            取消
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={createMutation.isPending}
          >
            <Sparkles className="h-4 w-4" />
            创建项目
          </Button>
        </div>
      </form>
    </Modal>
  );
};
