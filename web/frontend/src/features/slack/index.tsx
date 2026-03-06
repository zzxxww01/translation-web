import { useMemo } from 'react';
import { Lightbulb, RefreshCw, Send, User } from 'lucide-react';
import { Button, Textarea, useToast } from '../../components/ui';
import type { SlackReplyVariant } from '../../shared/types';
import { copyToClipboard, detectLanguage } from '../../shared/utils';
import { ReplySuggestions } from './components/ReplySuggestions';
import { useComposeReply, useGenerateReply } from './hooks';
import { useSlackWorkspaceStore } from './store';

export function SlackFeature() {
  const { showError, showSuccess } = useToast();
  const analyzeMutation = useGenerateReply();
  const composeMutation = useComposeReply();

  const {
    incomingText,
    incomingTranslation,
    incomingSuggestions,
    draftText,
    draftVersions,
    setIncomingText,
    setIncomingResult,
    clearIncoming,
    setDraftText,
    setDraftVersions,
    clearDraft,
  } = useSlackWorkspaceStore();

  const draftLanguage = useMemo(() => detectLanguage(draftText.trim()), [draftText]);

  const copyEnglishVersion = async (contentEn: string, successMessage: string) => {
    const copied = await copyToClipboard(contentEn);
    if (copied) {
      showSuccess(successMessage);
      return;
    }
    showError('复制失败');
  };

  const handleAnalyzeIncoming = async () => {
    const content = incomingText.trim();
    if (!content || analyzeMutation.isPending) {
      return;
    }

    try {
      const result = await analyzeMutation.mutateAsync({ message: content });
      setIncomingResult(result.translation, result.suggested_replies ?? []);
    } catch {
      // Error handled in mutation.
    }
  };

  const handleTranslateDraft = async () => {
    const content = draftText.trim();
    if (!content || composeMutation.isPending) {
      return;
    }

    if (draftLanguage === 'en') {
      showError('这里用于中文草稿。英文内容直接复制即可。');
      return;
    }

    try {
      const result = await composeMutation.mutateAsync({ content });
      setDraftVersions(
        result.versions.map((version: SlackReplyVariant) => ({
          ...version,
          chinese: version.chinese || content,
        }))
      );
    } catch {
      // Error handled in mutation.
    }
  };

  return (
    <div className="mx-auto grid h-full w-full max-w-7xl gap-6 p-6 xl:grid-cols-2">
      <section className="flex min-h-0 flex-col rounded-3xl border border-border-subtle bg-bg-card p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-text-secondary">
              <User className="h-4 w-4" />
              对方的话
            </div>
            <h2 className="mt-2 text-2xl font-semibold text-text-primary">英译中 + 建议回复</h2>
            <p className="mt-2 text-sm leading-6 text-text-muted">
              粘贴对方发来的英文消息，系统会给出中文理解和 A/B/C 三档英文建议回复。
            </p>
          </div>
          {(incomingTranslation || incomingSuggestions.length > 0) && (
            <button
              onClick={clearIncoming}
              className="text-sm text-text-muted transition-colors hover:text-text-primary"
              title="清空结果"
            >
              清空
            </button>
          )}
        </div>

        <div className="mt-5 flex-1">
          <Textarea
            value={incomingText}
            onChange={event => setIncomingText(event.target.value)}
            placeholder="Paste the incoming English message here..."
            className="min-h-[260px]"
            showCharCount={false}
          />
        </div>

        <div className="mt-4 flex gap-3">
          <Button
            size="md"
            variant="primary"
            onClick={handleAnalyzeIncoming}
            disabled={!incomingText.trim() || analyzeMutation.isPending}
            isLoading={analyzeMutation.isPending}
            className="flex-1"
          >
            <Lightbulb className="mr-2 h-4 w-4" />
            英译中 + 建议回复
          </Button>
          <Button
            size="md"
            variant="secondary"
            onClick={clearIncoming}
            disabled={!incomingText && !incomingTranslation && incomingSuggestions.length === 0}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            重置
          </Button>
        </div>

        {(incomingTranslation || incomingSuggestions.length > 0) && (
          <div className="mt-6 space-y-4">
            <div className="rounded-2xl border border-border-subtle bg-bg-secondary p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-text-muted">
                中文理解
              </div>
              <div className="whitespace-pre-wrap text-base leading-7 text-text-primary">
                {incomingTranslation || '暂无翻译结果'}
              </div>
            </div>

            <ReplySuggestions
              title="建议回复"
              options={incomingSuggestions}
              confirmLabel="复制这个版本"
              onSelectReply={contentEn => {
                void copyEnglishVersion(contentEn, '建议回复已复制');
              }}
              onClose={() => setIncomingResult(incomingTranslation, [])}
            />
          </div>
        )}
      </section>

      <section className="flex min-h-0 flex-col rounded-3xl border border-border-subtle bg-bg-card p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-text-secondary">
              <Send className="h-4 w-4" />
              我想回复的话
            </div>
            <h2 className="mt-2 text-2xl font-semibold text-text-primary">中译英</h2>
            <p className="mt-2 text-sm leading-6 text-text-muted">
              输入你的中文草稿，系统按 A/B/C 三档正式程度给出可直接发送的英文版本。
            </p>
          </div>
          {draftVersions.length > 0 && (
            <button
              onClick={clearDraft}
              className="text-sm text-text-muted transition-colors hover:text-text-primary"
              title="清空结果"
            >
              清空
            </button>
          )}
        </div>

        <div className="mt-5 flex-1">
          <Textarea
            value={draftText}
            onChange={event => setDraftText(event.target.value)}
            placeholder="输入你想回复的中文内容..."
            className="min-h-[260px]"
            showCharCount={false}
          />
        </div>

        <div className="mt-3 text-xs text-text-muted">
          {draftLanguage === 'en'
            ? '当前看起来已经是英文了，这里主要用于中文草稿。'
            : '支持中文或中英混合草稿，建议先把意思写清楚再生成版本。'}
        </div>

        <div className="mt-4 flex gap-3">
          <Button
            size="md"
            variant="primary"
            onClick={handleTranslateDraft}
            disabled={!draftText.trim() || composeMutation.isPending}
            isLoading={composeMutation.isPending}
            className="flex-1"
          >
            <Send className="mr-2 h-4 w-4" />
            中译英
          </Button>
          <Button
            size="md"
            variant="secondary"
            onClick={clearDraft}
            disabled={!draftText && draftVersions.length === 0}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            重置
          </Button>
        </div>

        {draftVersions.length > 0 && (
          <div className="mt-6">
            <ReplySuggestions
              title="英文版本"
              options={draftVersions}
              confirmLabel="复制这个版本"
              onSelectReply={contentEn => {
                void copyEnglishVersion(contentEn, '英文版本已复制');
              }}
              onClose={() => setDraftVersions([])}
            />
          </div>
        )}
      </section>
    </div>
  );
}
