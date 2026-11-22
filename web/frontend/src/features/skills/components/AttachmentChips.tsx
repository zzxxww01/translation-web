import { useEffect, useMemo, useRef, type ChangeEvent } from 'react';
import { ImagePlus, Paperclip, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { formatBytes } from '../state';
import { isImage } from '../input';

interface AttachmentPickerProps {
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
  compact?: boolean;
}

/** 本地图片的预览地址：组件卸载或换图时释放 */
function usePreview(file: File): string | null {
  const url = useMemo(
    () => (isImage(file.name) || file.type.startsWith('image/') ? URL.createObjectURL(file) : null),
    [file]
  );
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url);
  }, [url]);
  return url;
}

function Chip({ file, disabled, onRemove }: { file: File; disabled?: boolean; onRemove: () => void }) {
  const preview = usePreview(file);
  const remove = (
    <button
      type="button"
      className="shrink-0 text-text-muted hover:text-text-primary"
      onClick={onRemove}
      aria-label={`移除 ${file.name}`}
      disabled={disabled}
    >
      <X className="h-3.5 w-3.5" />
    </button>
  );
  if (preview) {
    return (
      <span
        className="relative inline-block h-14 w-14 overflow-hidden rounded-md border border-border-subtle bg-bg-secondary"
        title={`${file.name} · ${formatBytes(file.size)}`}
      >
        <img src={preview} alt={file.name} className="h-full w-full object-cover" />
        <span className="absolute right-0.5 top-0.5 inline-flex rounded bg-white/90 p-0.5 shadow-sm">{remove}</span>
      </span>
    );
  }
  return (
    <span className="inline-flex max-w-[16rem] items-center gap-1.5 rounded-md border border-border-subtle bg-bg-secondary px-2 py-1 text-xs text-text-secondary">
      <span className="truncate">{file.name}</span>
      <span className="shrink-0 text-text-muted">{formatBytes(file.size)}</span>
      {remove}
    </span>
  );
}

/** 选文件 / 选图片按钮 + 已选文件（图片显示缩略图）。同名文件按服务器规则自动改名，这里不去重。 */
export function AttachmentPicker({ files, onChange, disabled, compact }: AttachmentPickerProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const add = (event: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(event.target.files ?? []);
    if (picked.length) onChange([...files, ...picked]);
    event.target.value = '';
  };

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
      <input ref={fileRef} type="file" multiple className="hidden" onChange={add} />
      <input ref={imageRef} type="file" accept="image/*" multiple className="hidden" onChange={add} />
      <Button
        type="button"
        variant="ghost"
        size={compact ? 'icon' : 'sm'}
        disabled={disabled}
        onClick={() => fileRef.current?.click()}
        aria-label="添加附件"
        title="添加附件"
      >
        <Paperclip />
        {!compact && '添加附件'}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size={compact ? 'icon' : 'sm'}
        disabled={disabled}
        onClick={() => imageRef.current?.click()}
        aria-label="添加图片"
        title="添加图片（也可以直接粘贴截图）"
      >
        <ImagePlus />
        {!compact && '添加图片'}
      </Button>
      {files.map((file, index) => (
        <Chip
          key={`${file.name}-${file.size}-${index}`}
          file={file}
          disabled={disabled}
          onRemove={() => onChange(files.filter((_, i) => i !== index))}
        />
      ))}
    </div>
  );
}
