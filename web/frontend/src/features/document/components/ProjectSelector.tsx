import { type FC, useState } from 'react';
import { useDocumentStore } from '@/shared/stores';
import { useProjects, useDeleteProject } from '../hooks';
import { Button } from '@/components/ui/button-extended';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2 } from 'lucide-react';
import type { Project } from '@/shared/types';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ProjectSelectorProps {
  onNewProject: () => void;
}

export const ProjectSelector: FC<ProjectSelectorProps> = ({ onNewProject }) => {
  const { currentProject, setCurrentProject } = useDocumentStore();
  const { data: projects } = useProjects();
  const deleteProject = useDeleteProject();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);

  const handleProjectChange = (projectId: string) => {
    const project = projects?.find((p: Project) => p.id === projectId);
    if (project) {
      setCurrentProject(project);
    }
  };

  const handleDeleteClick = () => {
    if (currentProject) {
      setProjectToDelete(currentProject);
      setDeleteDialogOpen(true);
    }
  };

  const handleConfirmDelete = async () => {
    if (projectToDelete) {
      await deleteProject.mutateAsync(projectToDelete.id);
      setDeleteDialogOpen(false);
      setProjectToDelete(null);
    }
  };

  return (
    <div className="space-y-1.5">
      <Select value={currentProject?.id || ''} onValueChange={handleProjectChange}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder="选择项目..." />
        </SelectTrigger>
        <SelectContent>
          {projects?.map((project: Project) => {
            const title =
              project.title.length > 25
                ? project.title.substring(0, 25) + '...'
                : project.title;
            const percent = project.progress?.percent?.toFixed(0) || 0;
            return (
              <SelectItem key={project.id} value={project.id}>
                {title} ({percent}%)
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>

      <div className="flex gap-2">
        <Button
          variant="default"
          size="sm"
          onClick={onNewProject}
          className="flex-1"
          title="新建项目"
        >
          <Plus className="h-3.5 w-3.5" />
          新建
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDeleteClick}
          disabled={!currentProject || deleteProject.isPending}
          title="删除当前项目"
          className="group relative px-2.5 text-muted-foreground transition-all hover:text-destructive hover:bg-destructive/5 disabled:opacity-40"
        >
          <Trash2 className="h-3.5 w-3.5 transition-transform group-hover:scale-110" />
        </Button>
      </div>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-lg">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10">
                <Trash2 className="h-5 w-5 text-destructive" />
              </div>
              确认删除项目
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3 pt-2">
              <p className="text-sm leading-relaxed">
                确定要删除项目 <span className="font-semibold text-foreground">"{projectToDelete?.title}"</span> 吗？
              </p>
              <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3">
                <p className="text-xs text-destructive-foreground/80">
                  ⚠️ 此操作无法撤销，将永久删除：
                </p>
                <ul className="mt-2 space-y-1 text-xs text-destructive-foreground/70">
                  <li>• 所有章节和段落</li>
                  <li>• 翻译内容和进度</li>
                  <li>• 项目术语表</li>
                  <li>• 导出文件和缓存</li>
                </ul>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="gap-2 sm:gap-2">
            <AlertDialogCancel className="mt-0">取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90 focus:ring-destructive"
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
