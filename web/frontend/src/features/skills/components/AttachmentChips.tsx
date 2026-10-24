import { useRef } from 'react';
import { Paperclip, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { formatBytes } from '../state';

interface AttachmentPickerProps {
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
  compact?: boolean;
}

/** 选文件按钮 + 已选文件列表。同名文件按服务器规则自动改名，这里不去重。 */
export function AttachmentPicker({ files, onChange, disabled, compact }: AttachmentPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={event => {
          const picked = Array.from(event.target.files ?? []);
          if (picked.length) onChange([...files, ...picked]);
          event.target.value = '';
        }}
      />
      <Button
        type="button"
        variant="ghost"
        size={compact ? 'icon' : 'sm'}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        aria-label="添加附件"
        title="添加附件"
      >
        <Paperclip />
        {!compact && '添加附件'}
      </Button>
      {files.map((file, index) => (
        <span
          key={`${file.name}-${index}`}
          className="inline-flex max-w-[16rem] items-center gap-1.5 rounded-md border border-border-subtle bg-bg-secondary px-2 py-1 text-xs text-text-secondary"
        >
          <span className="truncate">{file.name}</span>
          <span className="shrink-0 text-text-muted">{formatBytes(file.size)}</span>
          <button
            type="button"
            className="shrink-0 text-text-muted hover:text-text-primary"
            onClick={() => onChange(files.filter((_, i) => i !== index))}
            aria-label={`移除 ${file.name}`}
            disabled={disabled}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </span>
      ))}
    </div>
  );
}
