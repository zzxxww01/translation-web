import { useMemo } from 'react';
import { toast } from 'sonner';
import { Lightbulb, Loader2, RefreshCw, Send, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import type { SlackReplyVariant } from '@/shared/types';
import { copyToClipboard, detectLanguage } from '@/shared/utils';
import { ReplySuggestions } from './components/ReplySuggestions';
import { useComposeReply, useGenerateReply } from './hooks';
import { useSlackWorkspaceStore } from './store';

export function SlackFeature() {
  const analyzeMutation = useGenerateReply();
  const composeMutation = useComposeReply();

  const {
    incomingText, incomingTranslation, incomingSuggestions,
    draftText, draftVersions,
    setIncomingText, setIncomingResult, clearIncoming,
    setDraftText, setDraftVersions, clearDraft,
  } = useSlackWorkspaceStore();

  const draftLanguage = useMemo(() => detectLanguage(draftText.trim()), [draftText]);

  const copyEnglish = async (content: string, msg: string) => {
    const ok = await copyToClipboard(content);
    if (ok) toast.success(msg);
    else toast.error('复制失败');
  };

  const handleAnalyze = async () => {
    const content = incomingText.trim();
    if (!content || analyzeMutation.isPending) return;
    try {
      const result = await analyzeMutation.mutateAsync({ message: content });
      setIncomingResult(result.translation, result.suggested_replies ?? []);
    } catch { /* handled */ }
  };

  const handleTranslateDraft = async () => {
    const content = draftText.trim();
    if (!content || composeMutation.isPending) return;
    if (draftLanguage === 'en') {
      toast.error('这里用于中文草稿。英文内容直接复制即可。');
      return;
    }
    try {
      const result = await composeMutation.mutateAsync({ content });
      setDraftVersions(
        result.versions.map((v: SlackReplyVariant) => ({ ...v, chinese: v.chinese || content }))
      );
    } catch { /* handled */ }
  };

  return (
    <div className="mx-auto grid h-full w-full max-w-7xl gap-6 p-6 xl:grid-cols-2">
      {/* Incoming panel */}
      <Card className="flex flex-col">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <User className="h-4 w-4" /> 对方的话
              </CardTitle>
              <CardDescription className="mt-1">
                粘贴英文消息，获取中文理解和 A/B/C 三档建议回复
              </CardDescription>
            </div>
            {(incomingTranslation || incomingSuggestions.length > 0) && (
              <Button variant="ghost" size="sm" onClick={clearIncoming}>清空</Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4">
          <Textarea
            value={incomingText}
            onChange={e => setIncomingText(e.target.value)}
            placeholder="Paste the incoming English message here..."
            className="min-h-[200px] flex-1"
          />
          <div className="flex gap-2">
            <Button
              onClick={handleAnalyze}
              disabled={!incomingText.trim() || analyzeMutation.isPending}
              className="flex-1"
            >
              {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lightbulb className="h-4 w-4" />}
              英译中 + 建议回复
            </Button>
            <Button
              variant="outline"
              onClick={clearIncoming}
              disabled={!incomingText && !incomingTranslation && incomingSuggestions.length === 0}
            >
              <RefreshCw className="h-4 w-4" /> 重置
            </Button>
          </div>

          {(incomingTranslation || incomingSuggestions.length > 0) && (
            <div className="space-y-4">
              <div className="rounded-lg border bg-muted/50 p-4">
                <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  中文理解
                </div>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {incomingTranslation || '暂无翻译结果'}
                </div>
              </div>
              <ReplySuggestions
                title="建议回复"
                options={incomingSuggestions}
                confirmLabel="复制这个版本"
                onSelectReply={en => copyEnglish(en, '建议回复已复制')}
                onClose={() => setIncomingResult(incomingTranslation, [])}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Draft panel */}
      <Card className="flex flex-col">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Send className="h-4 w-4" /> 我想回复的话
              </CardTitle>
              <CardDescription className="mt-1">
                输入中文草稿，按 A/B/C 三档正式程度生成英文版本
              </CardDescription>
            </div>
            {draftVersions.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearDraft}>清空</Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4">
          <Textarea
            value={draftText}
            onChange={e => setDraftText(e.target.value)}
            placeholder="输入你想回复的中文内容..."
            className="min-h-[200px] flex-1"
          />
          <p className="text-xs text-muted-foreground">
            {draftLanguage === 'en'
              ? '当前看起来已经是英文了，这里主要用于中文草稿。'
              : '支持中文或中英混合草稿，建议先把意思写清楚再生成版本。'}
          </p>
          <div className="flex gap-2">
            <Button
              onClick={handleTranslateDraft}
              disabled={!draftText.trim() || composeMutation.isPending}
              className="flex-1"
            >
              {composeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              中译英
            </Button>
            <Button variant="outline" onClick={clearDraft} disabled={!draftText && draftVersions.length === 0}>
              <RefreshCw className="h-4 w-4" /> 重置
            </Button>
          </div>

          {draftVersions.length > 0 && (
            <ReplySuggestions
              title="英文版本"
              options={draftVersions}
              confirmLabel="复制这个版本"
              onSelectReply={en => copyEnglish(en, '英文版本已复制')}
              onClose={() => setDraftVersions([])}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
