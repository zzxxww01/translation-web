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

  const versionLabels = ['简洁', '正式', '友好'];

  return (
    <div className="space-y-6">
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
          className="editorial-textarea min-h-[200px] resize-y text-sm"
          style={{
            fontFamily: 'var(--font-body)',
            borderColor: 'var(--color-border)'
          }}
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
        <Card className="workspace-container relative p-6">
          {/* Noise texture overlay */}
          <div
            className="absolute inset-0 pointer-events-none opacity-[0.03]"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
            }}
          />

          <div className="relative z-10 space-y-2">
            <div className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>💡 生成的版本</div>
            {currentVersions.map((version, index) => (
              <div
                key={version.version}
                className="version-card-animate"
                style={{ marginLeft: index === 1 ? '16px' : '0' }}
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
