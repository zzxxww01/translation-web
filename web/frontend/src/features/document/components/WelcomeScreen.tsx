import { ArrowRight, Clock3, FilePlus2, FolderOpen } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import type { Project } from '@/shared/types';
import { sortProjectsByRecency } from '../workflow';

interface WelcomeScreenProps {
  projects: Project[];
  lastProjectId?: string | null;
  onSelectProject: (project: Project) => void;
  onNewProject: () => void;
}

export function WelcomeScreen({
  projects,
  lastProjectId,
  onSelectProject,
  onNewProject,
}: WelcomeScreenProps) {
  const recentProjects = sortProjectsByRecency(projects).slice(0, 6);
  const lastProject =
    projects.find(project => project.id === lastProjectId) ?? recentProjects[0] ?? null;

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="mb-8 flex flex-col justify-between gap-4 border-b border-border-subtle pb-6 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">文档工作台</h1>
          <p className="mt-2 text-sm text-text-muted">继续未完成文档，或开始一个新项目。</p>
        </div>
        <Button
          type="button"
          variant="default"
          onClick={onNewProject}
          leftIcon={<FilePlus2 className="h-4 w-4" />}
        >
          新建项目
        </Button>
      </div>

      {lastProject && (
        <section className="mb-8" aria-labelledby="continue-project-heading">
          <h2 id="continue-project-heading" className="mb-3 text-sm font-semibold text-text-secondary">
            继续上次工作
          </h2>
          <button
            type="button"
            onClick={() => onSelectProject(lastProject)}
            className="flex w-full items-center justify-between gap-4 rounded-lg border border-primary-200 bg-primary-50/50 p-4 text-left transition-colors hover:border-primary-400 hover:bg-primary-50"
          >
            <div className="min-w-0">
              <div className="truncate font-medium text-text-primary">{lastProject.title}</div>
              <div className="mt-1 text-sm text-text-muted">
                已确认 {Math.round(lastProject.progress?.percent ?? 0)}%
              </div>
            </div>
            <ArrowRight className="h-5 w-5 shrink-0 text-primary-600" />
          </button>
        </section>
      )}

      <section aria-labelledby="recent-projects-heading">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 id="recent-projects-heading" className="text-sm font-semibold text-text-secondary">
            最近项目
          </h2>
          <span className="text-xs text-text-muted">共 {projects.length} 个</span>
        </div>

        {recentProjects.length > 0 ? (
          <div className="divide-y divide-border-subtle rounded-lg border border-border-subtle bg-bg-card">
            {recentProjects.map(project => (
              <button
                key={project.id}
                type="button"
                onClick={() => onSelectProject(project)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors first:rounded-t-lg last:rounded-b-lg hover:bg-bg-secondary"
              >
                <FolderOpen className="h-5 w-5 shrink-0 text-text-muted" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-text-primary">{project.title}</div>
                  <div className="mt-1 flex items-center gap-3 text-xs text-text-muted">
                    <span>已确认 {Math.round(project.progress?.percent ?? 0)}%</span>
                    {project.created_at && (
                      <span className="flex items-center gap-1">
                        <Clock3 className="h-3 w-3" />
                        {new Date(project.created_at).toLocaleDateString('zh-CN')}
                      </span>
                    )}
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-text-muted" />
              </button>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-text-muted">还没有文档项目</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onNewProject}
              className="mt-4"
              leftIcon={<FilePlus2 className="h-4 w-4" />}
            >
              新建第一个项目
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
