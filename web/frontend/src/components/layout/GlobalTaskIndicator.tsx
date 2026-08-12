import { useState } from 'react';
import { LoaderCircle, Square, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Progress } from '@/components/ui/progress';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useDocumentStore } from '@/shared/stores';
import { fullTranslationService } from '@/features/document/services/fullTranslationService';

/**
 * 后台翻译任务的收起式入口。
 *
 * 早前这里是一条通栏横幅，任何页面都被它顶掉一行高度。改成顶栏里的一个小按钮：
 * 平时只有一个转圈图标 + 百分比，点开才展示项目名、进度与取消。没有任务时整个
 * 按钮不渲染，不占位。
 */
export function GlobalTaskIndicator() {
  const navigate = useNavigate();
  const [isCancelling, setIsCancelling] = useState(false);
  const [open, setOpen] = useState(false);
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

  const openTask = () => {
    setOpen(false);
    navigate(`/document/${projectId}`);
  };

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
      setOpen(false);
      toast.success('翻译任务已取消');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '取消翻译失败');
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="flex h-9 items-center gap-1.5 rounded-md px-2.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          title={`正在翻译：${projectTitle}`}
          aria-label={`后台翻译任务，进度 ${percent}%，点击查看`}
        >
          <LoaderCircle className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
          <span className="tabular-nums">{percent}%</span>
        </button>
      </PopoverTrigger>

      <PopoverContent align="end" className="w-72" aria-live="polite">
        <p className="text-xs font-medium text-muted-foreground">后台翻译中</p>
        <p className="mt-1 truncate text-sm font-medium text-foreground" title={projectTitle}>
          {projectTitle}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {progress ? `${progress.current}/${progress.total} 段 · ${percent}%` : '正在准备'}
        </p>
        <Progress value={percent} className="mt-2.5 h-1.5" />
        <p className="mt-2.5 text-xs text-muted-foreground">
          任务在后台运行，关闭页面不会中断。
        </p>
        <div className="mt-3 flex gap-2">
          <Button type="button" size="sm" className="flex-1" onClick={openTask}>
            <ExternalLink className="h-4 w-4" />
            打开任务
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={cancel}
            disabled={isCancelling}
          >
            <Square className="h-4 w-4" />
            {isCancelling ? '取消中' : '取消'}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
