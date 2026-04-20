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

  return (
    <Card className="p-6 space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">📝 输入中文回复</label>
        <Textarea
          value={currentInput}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="输入你想说的中文内容..."
          className="min-h-[100px] resize-none"
          disabled={isGenerating}
        />
        <Button
          onClick={onGenerate}
          disabled={!currentInput.trim() || isGenerating}
          className="w-full"
        >
          {isGenerating ? (
            <>
              <Loader2 size={16} className="mr-2 animate-spin" />
              {buttonText}
            </>
          ) : (
            <>
              <Sparkles size={16} className="mr-2" />
              {buttonText}
            </>
          )}
        </Button>
      </div>

      {hasVersions && (
        <div className="space-y-3">
          <div className="text-sm font-medium">💡 生成的版本</div>
          {currentVersions.map((version, index) => (
            <VersionCard
              key={version.english}
              version={version}
              label={String.fromCharCode(65 + index)}
              onSelect={() => onSelectVersion(version)}
              disabled={isGenerating}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
