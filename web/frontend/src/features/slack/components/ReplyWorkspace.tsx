import { Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { VersionCard } from './VersionCard';
import type { SlackReplyVariant } from '@/shared/types';

interface ReplyWorkspaceProps {
  currentInput: string;
  currentVersions: SlackReplyVariant[];
  isGenerating: boolean;
  onInputChange: (value: string) => void;
  onGenerate: () => void;
  onSelectVersion: (version: SlackReplyVariant) => void;
}

export function ReplyWorkspace({
  currentInput,
  currentVersions,
  isGenerating,
  onInputChange,
  onGenerate,
  onSelectVersion,
}: ReplyWorkspaceProps) {
  const hasVersions = currentVersions.length > 0;
  const buttonText = isGenerating
    ? '生成中...'
    : hasVersions
    ? '重新生成'
    : '生成回复';

  const versionLabels = ['简洁', '正式', '友好'];

  return (
    <Card className="p-4 space-y-3">
      <div className="space-y-2">
        <label className="text-sm font-medium">
          📝 输入内容
          <span className="ml-2 text-xs text-muted-foreground font-normal">
            (粘贴对方英文 或 输入你的中文)
          </span>
        </label>
        <Textarea
          value={currentInput}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="粘贴对方的英文消息，或输入你想说的中文..."
          className="min-h-[80px] resize-none text-sm"
          disabled={isGenerating}
        />
        <Button
          onClick={onGenerate}
          disabled={!currentInput.trim() || isGenerating}
          className="w-full h-9"
        >
          {isGenerating ? (
            <>
              <Loader2 size={14} className="mr-2 animate-spin" />
              {buttonText}
            </>
          ) : (
            <>
              <Sparkles size={14} className="mr-2" />
              {buttonText}
            </>
          )}
        </Button>
      </div>

      {hasVersions && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-muted-foreground">💡 生成的版本</div>
          {currentVersions.map((version, index) => (
            <VersionCard
              key={version.english}
              version={version}
              label={versionLabels[index] || `版本${index + 1}`}
              onSelect={() => onSelectVersion(version)}
              disabled={isGenerating}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
