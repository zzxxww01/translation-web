import { Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
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
  onRefineVersion?: (updatedVersion: SlackReplyVariant) => void;
}

export function ReplyWorkspace({
  currentInput,
  currentVersions,
  isGenerating,
  onInputChange,
  onGenerate,
  onSelectVersion,
  onRefineVersion,
}: ReplyWorkspaceProps) {
  const hasVersions = currentVersions.length > 0;
  const buttonText = isGenerating
    ? '生成中...'
    : hasVersions
    ? '重新生成'
    : '生成回复';

  const versionLabels = ['简洁', '标准', '正式'];

  return (
    <div className="space-y-6 w-full">
      <div className="space-y-2 w-full">
        <Textarea
          value={currentInput}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="粘贴对方的英文消息，或输入你想说的中文..."
          className="editorial-textarea min-h-[150px] resize-y text-sm w-full"
          style={{
            fontFamily: 'var(--font-body)',
            borderColor: 'var(--color-border)'
          }}
          disabled={isGenerating}
        />
        <Button
          onClick={onGenerate}
          disabled={!currentInput.trim() || isGenerating}
          className="h-10 w-full"
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
        <Card className="relative bg-bg-tertiary p-5 sm:p-6">
          <div className="relative space-y-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-500">生成的版本</div>
            {currentVersions.map((version, index) => (
              <div
                key={version.version}
                className="version-card-animate"
              >
                <VersionCard
                  version={version}
                  label={versionLabels[index] || `版本${index + 1}`}
                  onSelect={() => onSelectVersion(version)}
                  onRefine={onRefineVersion}
                  disabled={isGenerating}
                />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
