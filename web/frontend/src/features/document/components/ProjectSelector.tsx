import { type FC } from 'react';
import { useDocumentStore } from '../../../shared/stores';
import { useProjects } from '../hooks';
import { Button } from '../../../components/ui';
import { Plus } from 'lucide-react';
import type { Project } from '../../../shared/types';

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
      <select
        value={currentProject?.id || ''}
        onChange={(e) => handleProjectChange(e.target.value)}
        className="w-full rounded-md border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="">选择项目...</option>
        {projects?.map((project: Project) => {
          const title =
            project.title.length > 25
              ? project.title.substring(0, 25) + '...'
              : project.title;
          const percent = project.progress?.percent?.toFixed(0) || 0;
          return (
            <option key={project.id} value={project.id}>
              {title} ({percent}%)
            </option>
          );
        })}
      </select>

      <div className="flex gap-2">
        <Button
          variant="primary"
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
