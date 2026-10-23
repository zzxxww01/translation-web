import { ArrowRight, ArrowUpRight, FilePlus2 } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import { PageHeader } from '@/components/layout/PageHeader';
import { cn } from '@/lib/utils';
import type { Project } from '@/shared/types';
import { sortProjectsByRecency } from '../workflow';

interface WelcomeScreenProps {
  projects: Project[];
  lastProjectId?: string | null;
  onSelectProject: (project: Project) => void;
  onNewProject: () => void;
}

const percentOf = (project: Project) =>
  Math.min(100, Math.max(0, Math.round(project.progress?.percent ?? 0)));

const formatDate = (value?: string) =>
  value
    ? new Date(value).toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
    : null;

function ProgressLine({ percent, className }: { percent: number; className?: string }) {
  return (
    <div
      className={cn('h-1 overflow-hidden rounded-full bg-primary-100', className)}
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full bg-primary-500 transition-[width] duration-500"
        style={{ width: `${percent}%` }}
      />
    </div>
  );
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

  const inProgress = projects.filter(project => percentOf(project) > 0 && percentOf(project) < 100).length;
  const completed = projects.filter(project => percentOf(project) >= 100).length;
  const averagePercent = projects.length
    ? Math.round(projects.reduce((sum, project) => sum + percentOf(project), 0) / projects.length)
    : 0;
  const stats = [
    { label: '全部项目', value: projects.length },
    { label: '进行中', value: inProgress },
    { label: '已完成', value: completed },
    { label: '平均确认进度', value: `${averagePercent}%` },
  ];

  return (
    <div className="mx-auto w-full max-w-5xl px-5 pb-16 pt-10 sm:px-8 sm:pt-14">
      <PageHeader
        eyebrow="长文翻译 · Longform"
        title="文档工作台"
        description="把英文长文逐段译成可发布的中文稿。继续未完成的文档，或开始一个新项目。"
        actions={
          <Button
            type="button"
            variant="default"
            onClick={onNewProject}
            leftIcon={<FilePlus2 className="h-4 w-4" />}
          >
            新建项目
          </Button>
        }
      />

      {projects.length > 0 && (
        <dl className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border-subtle bg-border-subtle sm:grid-cols-4">
          {stats.map(stat => (
            <div key={stat.label} className="bg-white px-5 py-4">
              <dt className="text-xs text-text-muted">{stat.label}</dt>
              <dd
                className="mt-1 text-[26px] font-semibold leading-none tabular-nums text-text-primary"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                {stat.value}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {lastProject && (
        <section className="mt-10" aria-labelledby="continue-project-heading">
          <h2 id="continue-project-heading" className="sr-only">
            继续上次工作
          </h2>
          <button
            type="button"
            onClick={() => onSelectProject(lastProject)}
            className="card-glass group relative block w-full overflow-hidden p-6 text-left transition-shadow hover:shadow-[0_1px_2px_rgba(67,26,48,0.05),0_20px_44px_-24px_rgba(67,26,48,0.3)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-8"
          >
            <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-primary-500" />
            <div className="flex items-start justify-between gap-6">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-500">
                  继续上次工作
                </p>
                <p
                  className="mt-3 text-xl leading-snug text-text-primary sm:text-2xl"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {lastProject.title}
                </p>
                <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-text-muted">
                  <span>
                    已确认 <span className="font-medium tabular-nums text-text-secondary">{percentOf(lastProject)}%</span>
                  </span>
                  {lastProject.progress?.total_paragraphs ? (
                    <span className="tabular-nums">
                      {lastProject.progress.approved} / {lastProject.progress.total_paragraphs} 段
                    </span>
                  ) : null}
                  {formatDate(lastProject.created_at) && <span>创建于 {formatDate(lastProject.created_at)}</span>}
                </p>
              </div>
              <span className="hidden shrink-0 items-center gap-1.5 rounded-full border border-primary-200 bg-primary-50 px-4 py-2 text-sm font-medium text-primary-700 transition-colors group-hover:border-primary-500 group-hover:bg-primary-500 group-hover:text-white sm:inline-flex">
                继续翻译
                <ArrowRight className="h-4 w-4" />
              </span>
            </div>
            <ProgressLine percent={percentOf(lastProject)} className="mt-6" />
          </button>
        </section>
      )}

      <section className="mt-12" aria-labelledby="recent-projects-heading">
        <div className="mb-4 flex items-baseline justify-between gap-3">
          <h2 id="recent-projects-heading" className="text-xl text-text-primary">
            最近项目
          </h2>
          <span className="text-xs tabular-nums text-text-muted">共 {projects.length} 个</span>
        </div>

        {recentProjects.length > 0 ? (
          <ol className="divide-y divide-border-subtle overflow-hidden rounded-xl border border-border-subtle bg-white">
            {recentProjects.map((project, index) => (
              <li key={project.id}>
                <button
                  type="button"
                  onClick={() => onSelectProject(project)}
                  className="group flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-[#fdf8fa] focus-visible:bg-[#fdf8fa] focus-visible:outline-none sm:gap-5"
                >
                  <span
                    className="w-6 shrink-0 text-sm tabular-nums text-primary-300"
                    style={{ fontFamily: 'var(--font-display)' }}
                  >
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[15px] font-medium text-text-primary group-hover:text-primary-700">
                      {project.title}
                    </div>
                    {formatDate(project.created_at) && (
                      <div className="mt-1 text-xs text-text-muted">{formatDate(project.created_at)}</div>
                    )}
                  </div>
                  <div className="hidden w-32 shrink-0 items-center gap-3 sm:flex">
                    <ProgressLine percent={percentOf(project)} className="flex-1" />
                    <span className="w-9 text-right text-xs tabular-nums text-text-muted">{percentOf(project)}%</span>
                  </div>
                  <span className="text-xs tabular-nums text-text-muted sm:hidden">{percentOf(project)}%</span>
                  <ArrowUpRight className="h-4 w-4 shrink-0 text-text-disabled transition-colors group-hover:text-primary-500" />
                </button>
              </li>
            ))}
          </ol>
        ) : (
          <div className="rounded-xl border border-dashed border-border bg-white/60 px-6 py-14 text-center">
            <p className="text-lg text-text-primary" style={{ fontFamily: 'var(--font-display)' }}>
              还没有文档项目
            </p>
            <p className="mt-2 text-sm text-text-muted">导入一篇英文长文，开始第一份译稿。</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onNewProject}
              className="mt-5"
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
