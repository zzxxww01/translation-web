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
          variant="destructive"
          size="sm"
          onClick={handleDeleteClick}
          disabled={!currentProject || deleteProject.isPending}
          title="删除当前项目"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除项目</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除项目 "{projectToDelete?.title}" 吗？
              <br />
              此操作无法撤销，将永久删除项目的所有数据。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
