import { useState } from 'react';
import { LoaderCircle, Square, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Progress } from '@/components/ui/progress';
import { useDocumentStore } from '@/shared/stores';
import { fullTranslationService } from '@/features/document/services/fullTranslationService';

export function GlobalTaskTray() {
  const navigate = useNavigate();
  const [isCancelling, setIsCancelling] = useState(false);
  const isActive = useDocumentStore(state => state.isFullTranslating);
  const progress = useDocumentStore(state => state.fullTranslateProgress);
  const projectId = useDocumentStore(state => state.fullTranslateProjectId);
  const currentProject = useDocumentStore(state => state.currentProject);
  const endFullTranslate = useDocumentStore(state => state.endFullTranslate);

  if (!isActive || !projectId) {
    return null;
  }

  const percent =
    progress && progress.total > 0
      ? Math.min(100, Math.round((progress.current / progress.total) * 100))
      : 0;
  const projectTitle =
    currentProject?.id === projectId ? currentProject.title || projectId : projectId;

  const cancel = async () => {
    setIsCancelling(true);
    try {
      if (
        fullTranslationService.isTranslating() &&
        fullTranslationService.getProjectId() === projectId
      ) {
        await fullTranslationService.stopTranslation();
      } else {
        const response = await fetch(`/api/projects/${projectId}/translation-cancel`, {
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error(`取消失败：${response.status}`);
        }
      }
      endFullTranslate(projectId);
      toast.success('翻译任务已取消');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '取消翻译失败');
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <section
      className="relative z-30 flex min-h-11 items-center gap-3 border-b border-indigo-100 bg-indigo-50 px-3 py-2 text-sm md:px-6"
      aria-label="后台任务"
      aria-live="polite"
    >
      <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden="true" />
      <button
        type="button"
        className="min-w-0 flex-1 text-left"
        onClick={() => navigate(`/document/${projectId}`)}
      >
        <span className="block truncate font-medium text-foreground">
          正在翻译：{projectTitle}
        </span>
        <span className="block text-xs text-muted-foreground">
          {progress ? `${progress.current}/${progress.total} 段 · ${percent}%` : '正在准备'}
        </span>
      </button>
      <Progress value={percent} className="hidden h-1.5 w-28 sm:block" />
      <Button
        variant="ghost"
        size="icon"
        onClick={() => navigate(`/document/${projectId}`)}
        title="打开任务"
        aria-label="打开翻译任务"
      >
        <ExternalLink className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={cancel}
        disabled={isCancelling}
        title="取消任务"
        aria-label="取消翻译任务"
      >
        <Square className="h-4 w-4" />
      </Button>
    </section>
  );
}
