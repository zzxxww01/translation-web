import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { usePostStore } from '@/shared/stores';
import { useTranslatePost, useOptimizePost, useGenerateTitle } from './hooks';
import { TranslationVersionType } from '@/shared/constants';
import { SourceInput } from './components/SourceInput';
import { TranslationOutput } from './components/TranslationOutput';
import { OptimizationPanel } from './components/OptimizationPanel';
import { TitleGenerator } from './components/TitleGenerator';

export function PostFeature() {
  const {
    originalText, versions, currentVersionId, isEdited, editedContent, isLoading,
    setOriginalText, addVersion, setCurrentVersion, setEditedContent,
    saveEdit, discardEdit, clear, setLoading,
  } = usePostStore();

  const translateMutation = useTranslatePost();
  const optimizeMutation = useOptimizePost();
  const generateTitleMutation = useGenerateTitle();
  const [customInstruction, setCustomInstruction] = useState('');

  const currentContent = isEdited ? editedContent : versions.find(v => v.id === currentVersionId)?.content || '';

  const handleTranslate = useCallback(async () => {
    if (!originalText.trim()) return;
    setLoading(true);
    try {
      const result = await translateMutation.mutateAsync({ content: originalText });
      if (!result.translation?.trim()) {
        toast.error('翻译失败：服务器返回了空内容');
        return;
      }
      addVersion(result.translation, TranslationVersionType.TRANSLATION);
    } catch (error) {
      console.error('翻译失败:', error);
    } finally {
      setLoading(false);
    }
  }, [originalText, setLoading, translateMutation, addVersion]);

  const handleOptimize = useCallback(async (options: { instruction?: string; optionId?: string }) => {
    if (!originalText) return;
    const currentVersion = versions.find(v => v.id === currentVersionId);
    if (!currentVersion) {
      toast.error('请先进行翻译');
      return;
    }
    setLoading(true);
    try {
      const result = await optimizeMutation.mutateAsync({
        original_text: originalText,
        current_translation: currentVersion.content,
        instruction: options.instruction,
        option_id: options.optionId,
        conversation_history: versions.filter(v => v.instruction).slice(-3)
          .map(v => ({ role: 'user', content: v.instruction || '' })),
      });
      if (!result.optimized_translation?.trim()) {
        toast.error('优化失败：服务器返回了空内容');
        return;
      }
      addVersion(
        result.optimized_translation,
        TranslationVersionType.OPTIMIZATION,
        options.optionId ? `[${options.optionId}]` : options.instruction
      );
    } catch (error) {
      console.error('优化失败:', error);
    } finally {
      setLoading(false);
    }
  }, [originalText, versions, currentVersionId, setLoading, optimizeMutation, addVersion]);

  const handleGenerateTitle = useCallback(async (instruction?: string): Promise<string[]> => {
    const currentVersion = versions.find(v => v.id === currentVersionId);
    const content = currentVersion?.content || editedContent || originalText;
    if (!content || content.trim().length < 50) return [];
    setLoading(true);
    try {
      const result = await generateTitleMutation.mutateAsync({
        content,
        instruction: instruction || undefined,
      });
      return result.title.split('\n').filter((t: string) => t.trim()).slice(0, 8);
    } finally {
      setLoading(false);
    }
  }, [versions, currentVersionId, editedContent, originalText, setLoading, generateTitleMutation]);

  const handleClear = () => {
    setOriginalText('');
    clear();
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'Enter') {
        const active = document.activeElement as HTMLElement;
        if (active?.id === 'postSourceInput') {
          e.preventDefault();
          handleTranslate();
        }
      }
      if (e.ctrlKey && e.key === 'k') {
        const active = document.activeElement as HTMLElement;
        if (active?.id === 'customInstructionInput' || active?.id === 'translationEditor') {
          e.preventDefault();
          if (customInstruction.trim()) {
            handleOptimize({ instruction: customInstruction });
            setCustomInstruction('');
          } else {
            document.getElementById('customInstructionInput')?.focus();
          }
        }
      }
      if (e.key === 'Escape' && isEdited) {
        discardEdit();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [customInstruction, discardEdit, handleOptimize, handleTranslate, isEdited]);

  return (
    <div className="flex h-full overflow-auto">
      <div className="mx-auto w-full max-w-7xl p-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold">帖子翻译</h2>
          <p className="text-sm text-muted-foreground">翻译、优化并生成标题</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-h-[calc(100vh-200px)]">
          <SourceInput
            value={originalText}
            onChange={setOriginalText}
            onTranslate={handleTranslate}
            onClear={handleClear}
            isLoading={isLoading}
            canClear={!!(originalText.trim() || versions.length > 0 || currentContent)}
          />

          <div className="flex flex-col gap-5">
            <TranslationOutput
              versions={versions}
              currentVersionId={currentVersionId}
              currentContent={currentContent}
              isEdited={isEdited}
              editedContent={editedContent}
              onSetCurrentVersion={setCurrentVersion}
              onSetEditedContent={setEditedContent}
              onSaveEdit={saveEdit}
              onDiscardEdit={discardEdit}
            />

            <OptimizationPanel
              onOptimize={handleOptimize}
              isLoading={isLoading}
              hasVersions={versions.length > 0}
              hasOriginal={!!originalText}
            />

            <TitleGenerator
              onGenerate={handleGenerateTitle}
              isLoading={isLoading}
              canGenerate={versions.length > 0 || !!originalText}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
