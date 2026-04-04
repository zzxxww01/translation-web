import { type FC } from 'react';
import { useDocumentStore } from '@/shared/stores';
import { useProjects } from '../hooks';
import { Button } from '@/components/ui/button-extended';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus } from 'lucide-react';
import type { Project } from '@/shared/types';

interface ProjectSelectorProps {
  onNewProject: () => void;
}

export const ProjectSelector: FC<ProjectSelectorProps> = ({ onNewProject }) => {
  const { currentProject, setCurrentProject } = useDocumentStore();
  const { data: projects } = useProjects();

  const handleProjectChange = (projectId: string) => {
    const project = projects?.find((p: Project) => p.id === projectId);
    if (project) {
      setCurrentProject(project);
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
      </div>
    </div>
  );
};
