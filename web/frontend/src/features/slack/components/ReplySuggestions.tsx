import { type FC, useMemo, useState } from 'react';
import { Check, Copy, Edit3, X } from 'lucide-react';
import type { SlackReplyVariant } from '../../../shared/types';
import { Button } from '../../../components/ui';
import { Textarea } from '../../../components/ui';
import { copyToClipboard } from '../../../shared/utils';
import { useToast } from '../../../components/ui';

interface ReplySuggestionsProps {
  title: string;
  options: SlackReplyVariant[];
  onSelectReply: (contentEn: string, contentCn: string) => void;
  onClose: () => void;
  confirmLabel?: string;
}

const VERSION_META: Record<string, { label: string; description: string }> = {
  A: {
    label: '版本 A',
    description: '最 casual，适合同级快速沟通',
  },
  B: {
    label: '版本 B',
    description: '标准职场 casual，适合跨部门协作',
  },
  C: {
    label: '版本 C',
    description: '稍正式，适合上司或大群',
  },
};

export const ReplySuggestions: FC<ReplySuggestionsProps> = ({
  title,
  options,
  onSelectReply,
  onClose,
  confirmLabel = '使用这个版本',
}) => {
  const { showSuccess } = useToast();
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');

  const orderedOptions = useMemo(
    () => [...options].sort((a, b) => a.version.localeCompare(b.version)),
    [options]
  );

  const selectedOption = orderedOptions.find(option => option.version === selectedVersion) ?? null;

  const handleSelect = (option: SlackReplyVariant) => {
    setSelectedVersion(option.version);
    setEditedContent(option.english);
    setIsEditing(false);
  };

  const handleCopy = async (content: string) => {
    await copyToClipboard(content);
    showSuccess('已复制到剪贴板');
  };

  const handleConfirm = () => {
    if (!selectedOption) return;
    onSelectReply(isEditing ? editedContent : selectedOption.english, selectedOption.chinese ?? '');
  };

  if (orderedOptions.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 rounded-lg border border-border-subtle bg-bg-secondary p-4">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-medium text-text-primary">{title}</h4>
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text-primary"
          title="关闭"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-2">
        {orderedOptions.map(option => {
          const meta = VERSION_META[option.version] ?? {
            label: `版本 ${option.version}`,
            description: '',
          };

          return (
            <div
              key={option.version}
              onClick={() => handleSelect(option)}
              className={`cursor-pointer rounded-lg border p-3 transition-all ${
                selectedVersion === option.version
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-border-subtle hover:border-border hover:bg-bg-tertiary'
              }`}
            >
              <div className="mb-1 flex items-center justify-between gap-3">
                <span className="text-xs font-medium text-text-muted">{meta.label}</span>
                <span className="text-xs text-text-muted">{meta.description}</span>
              </div>
              <p className="text-sm text-text-primary">{option.english}</p>
              {option.chinese && (
                <p className="mt-1 text-xs text-text-muted">中文参考: {option.chinese}</p>
              )}

              {selectedVersion === option.version && (
                <div className="mt-2 flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={event => {
                      event.stopPropagation();
                      handleCopy(option.english);
                    }}
                  >
                    <Copy className="mr-1 h-3 w-3" />
                    复制
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={event => {
                      event.stopPropagation();
                      setIsEditing(current => !current);
                    }}
                  >
                    <Edit3 className="mr-1 h-3 w-3" />
                    编辑
                  </Button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {isEditing && selectedOption && (
        <div className="mt-3">
          <Textarea
            value={editedContent}
            onChange={event => setEditedContent(event.target.value)}
            placeholder="编辑英文回复..."
            className="min-h-[72px]"
            showCharCount={false}
          />
        </div>
      )}

      {selectedOption && (
        <div className="mt-3 flex justify-end">
          <Button variant="primary" size="sm" onClick={handleConfirm}>
            <Check className="mr-1 h-4 w-4" />
            {confirmLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
