import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { AlertCircle, ArrowLeft, Bot, Download, ExternalLink, MoreHorizontal, PanelLeft, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { isUnauthorized } from '@/features/skills/hooks';
import { articlesApi, downloadText } from '../api';
import { articleKeys, useClaudeRun, useWorkbench } from '../hooks';
import { importClaudeTrack, NoClaudeOutput, startClaudeTrack } from '../lib/claude';
import { unsavedEdits } from '../lib/edits';
import { loadCollapsed, PANES, saveCollapsed, togglePane, type Collapsed } from '../lib/panes';
import { canFillMissing, countFilled, SECOND_MODELS, TERMS_STEP, trackSummary } from '../lib/tracks';
import type { PaneId, Workbench as WorkbenchData, WorkbenchRow, WorkbenchVariant } from '../types';
import { PaneGrid, type PaneColumn } from './PaneGrid';
import { TrackDrawer, type DrawerState } from './TrackDrawer';

function useIsMobile(): boolean {
  const query = '(max-width: 767px)';
  const [mobile, setMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia?.(query)?.matches);
  useEffect(() => {
    const list = window.matchMedia?.(query);
    if (!list) return;
    const update = () => setMobile(list.matches);
    list.addEventListener('change', update);
    return () => list.removeEventListener('change', update);
  }, []);
  return Boolean(mobile);
}

const TONE: Record<string, string> = {
  busy: 'bg-info-light text-info',
  wait: 'bg-warning-light text-warning',
  done: 'bg-success-light text-success',
  error: 'bg-error-light text-error',
  idle: 'bg-bg-tertiary text-text-muted',
};

function StatusChip({ label, text, tone }: { label: string; text: string; tone: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs', TONE[tone])}>
      <span className="font-medium">{label}</span>
      <span>{text}</span>
    </span>
  );
}

function isQaBlocked(error: unknown): boolean {
  return error instanceof Error && error.message.includes('QA');
}

interface WorkbenchProps {
  projectId: string;
  onShowList?: () => void;
}

export function Workbench({ projectId, onShowList }: WorkbenchProps) {
  const query = useWorkbench(projectId);
  if (query.isPending) {
    return <div className="flex h-full items-center justify-center text-sm text-text-muted">读取文章…</div>;
  }
  if (query.error || !query.data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-text-muted">
        <p>打不开这篇文章：{query.error?.message ?? '未知错误'}</p>
        <Link to="/articles" className="text-primary-700 underline">回到文章列表</Link>
      </div>
    );
  }
  return <WorkbenchView data={query.data} onShowList={onShowList} />;
}

function WorkbenchView({ data, onShowList }: { data: WorkbenchData; onShowList?: () => void }) {
  const { project, variants, rows } = data;
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState<Collapsed>(loadCollapsed);
  const [mobilePane, setMobilePane] = useState<PaneId>('web');
  const [variantId, setVariantId] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<DrawerState>(null);
  const [claudeNote, setClaudeNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const importTried = useRef<string | null>(null);

  const variant: WorkbenchVariant | null = variants.find(v => v.id === variantId) ?? variants[0] ?? null;
  const claudeRun = useClaudeRun(project.claude_run_id);
  const claudeVariant = variants.find(v => v.kind === 'claude');
  const refresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: articleKeys.workbench(project.id) }),
    [queryClient, project.id]
  );

  // 离开页面时还有没存下的修改就提醒
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!unsavedEdits.any()) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, []);

  // Claude 任务结束了还没导入：自动取回 zh.md 导入（每个任务只自动试一次）
  const run = claudeRun.data;
  useEffect(() => {
    if (!run || run.status !== 'idle' || importTried.current === run.id) return;
    if (claudeVariant?.import?.run_id === run.id) return;
    importTried.current = run.id;
    importClaudeTrack(project.id, run.id)
      .then(result => {
        toast.success(`Claude 译文已导入：对上 ${result.aligned} 段`);
        setClaudeNote(null);
        return refresh();
      })
      .catch(error => setClaudeNote(error instanceof NoClaudeOutput ? error.message : `Claude 译文导入失败：${error.message}`));
  }, [run, claudeVariant, project.id, refresh]);

  const toggle = (pane: PaneId) => {
    setCollapsed(current => {
      const next = togglePane(current, pane);
      saveCollapsed(next);
      return next;
    });
  };

  const save = useCallback(async (target: string, row: WorkbenchRow, text: string) => {
    await articlesApi.saveText(project.id, { target, section_id: row.section_id, paragraph_id: row.paragraph_id, text });
    queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
      ...current,
      rows: current.rows.map(item => item.key !== row.key ? item : target === project.id
        ? { ...item, web: text }
        : { ...item, alt: { ...item.alt, [target]: text } }),
    });
  }, [project.id, queryClient]);

  const exportVersion = async (target: string, format: 'zh' | 'en') => {
    try {
      const result = await articlesApi.exportMarkdown(target, format);
      downloadText(result.filename, result.content);
    } catch (error) {
      if (format === 'zh' && isQaBlocked(error) && window.confirm(`${(error as Error).message}\n\n仍然导出？`)) {
        const result = await articlesApi.exportMarkdown(target, format, true);
        downloadText(result.filename, result.content);
        return;
      }
      toast.error(error instanceof Error ? error.message : '导出失败');
    }
  };

  const startModelVariant = async (model: string, label: string) => {
    setBusy(true);
    try {
      const { variant_id } = await articlesApi.createModelVariant(project.id, model, label);
      await articlesApi.startWorkflow(variant_id, { model, autoAcceptTerms: true });
      setVariantId(variant_id);
      toast.success(`译本 2 开始用 ${label} 翻译`);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能开始');
    } finally {
      setBusy(false);
    }
  };

  const fillMissing = async (target: string, model?: string) => {
    try {
      await articlesApi.startWorkflow(target, { model, autoAcceptTerms: true });
      toast.success('开始补译缺的段，已有的不动');
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能开始补译');
    }
  };

  const startClaude = async () => {
    setBusy(true);
    try {
      await startClaudeTrack(project.id);
      setClaudeNote(null);
      importTried.current = null;
      toast.success('已交给 Claude；它提问时这里会提示你');
      await refresh();
    } catch (error) {
      toast.error(isUnauthorized(error) ? '先去 Claude 页登录一次（只需一次）' : error instanceof Error ? error.message : '没能交给 Claude');
    } finally {
      setBusy(false);
    }
  };

  const webFilled = countFilled(rows, row => row.web);
  const webSummary = trackSummary(project.status, webFilled);
  const altFilled = variant ? countFilled(rows, row => row.alt[variant.id] ?? null) : null;
  const altSummary = variant && altFilled ? trackSummary(variant.status, altFilled) : null;
  const title = project.title_translation || variant?.title_translation || project.title;
  const webWaitingTerms = project.status.active && project.status.current_step === TERMS_STEP && project.status.run_id;

  const columns = useMemo<Record<PaneId, PaneColumn>>(() => {
    const altLabel = variant ? `译本 2 · ${variant.label}` : '译本 2';
    return {
      source: {
        id: 'source',
        title: '英文',
        header: (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-secondary">英文</span>
            <button type="button" title="导出英文原文" onClick={() => void exportVersion(project.id, 'en')} className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary">
              <Download className="h-3.5 w-3.5" />
            </button>
          </div>
        ),
      },
      web: {
        id: 'web',
        title: '译本 1',
        header: (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-secondary">译本 1 · 网页版</span>
            <span className="text-xs text-text-muted" title={project.status.current_step ?? undefined}>{webSummary.text}</span>
            {canFillMissing(project.status, webFilled) && (
              <button type="button" onClick={() => void fillMissing(project.id)} className="rounded-md px-1.5 text-xs text-primary-700 hover:bg-primary-50">补译</button>
            )}
            <button type="button" title="导出译本 1" onClick={() => void exportVersion(project.id, 'zh')} className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary">
              <Download className="h-3.5 w-3.5" />
            </button>
          </div>
        ),
        text: row => row.web,
        save: (row, text) => save(project.id, row, text),
        placeholder: project.status.active ? '翻译中…' : '还没有译文，可以直接写',
        adopt: variant ? { label: variant.label, text: row => row.alt[variant.id] ?? null } : undefined,
      },
      alt: {
        id: 'alt',
        title: '译本 2',
        header: (
          <div className="flex flex-wrap items-center gap-2">
            {variants.length > 1 ? (
              <select
                aria-label="选择译本 2"
                value={variant?.id}
                onChange={event => setVariantId(event.target.value)}
                className="rounded-md border border-border-subtle bg-white px-1.5 py-0.5 text-sm text-text-secondary"
              >
                {variants.map(item => <option key={item.id} value={item.id}>译本 2 · {item.label}</option>)}
              </select>
            ) : (
              <span className="text-sm font-medium text-text-secondary">{altLabel}</span>
            )}
            {altSummary && <span className="text-xs text-text-muted" title={variant?.status.current_step ?? undefined}>{altSummary.text}</span>}
            {variant && variant.kind === 'model' && altFilled && canFillMissing(variant.status, altFilled) && (
              <button
                type="button"
                onClick={() => void fillMissing(variant.id, SECOND_MODELS.find(option => option.label === variant.label)?.model)}
                className="rounded-md px-1.5 text-xs text-primary-700 hover:bg-primary-50"
              >
                补译
              </button>
            )}
            {variant && (
              <button type="button" title="导出译本 2" onClick={() => void exportVersion(variant.id, 'zh')} className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary">
                <Download className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        ),
        ...(variant
          ? {
              text: (row: WorkbenchRow) => row.alt[variant.id] ?? null,
              save: (row: WorkbenchRow, text: string) => save(variant.id, row, text),
              placeholder: variant.status.active ? '翻译中…' : '还没有译文，可以直接写',
              adopt: { label: '译本 1', text: (row: WorkbenchRow) => row.web },
            }
          : { text: () => null, save: async () => undefined, placeholder: '' }),
      },
    };
    // exportVersion 只依赖 project/variant，跟着它们变
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, project.status.active, variant, variants, webSummary.text, altSummary?.text, save]);

  const claudeWaiting = run?.status === 'waiting';
  const claudeRunning = run?.status === 'running';

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="border-b border-border-subtle bg-bg-primary px-4 py-2.5 md:px-6">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          {onShowList ? (
            <button type="button" onClick={onShowList} title="显示文章列表" className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary">
              <PanelLeft className="h-4 w-4" />
            </button>
          ) : (
            <button type="button" onClick={() => navigate('/articles')} title="回到文章列表" className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary">
              <ArrowLeft className="h-4 w-4" />
            </button>
          )}
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-[17px] leading-snug text-text-primary [font-family:var(--font-display)]" title={project.title}>{title}</h1>
            {title !== project.title && <p className="truncate text-xs text-text-muted">{project.title}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <StatusChip label="网页版" text={webSummary.text} tone={webSummary.tone} />
            {variant && altSummary && <StatusChip label={variant.label} text={altSummary.text} tone={altSummary.tone} />}
            {(claudeRunning || claudeWaiting) && !claudeVariant && (
              <StatusChip label="Claude" text={claudeWaiting ? '在等你回答' : '翻译中'} tone={claudeWaiting ? 'wait' : 'busy'} />
            )}
          </div>
          <div className="flex items-center gap-1">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="outline"><Download /> 导出</Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => void exportVersion(project.id, 'en')}>英文原文</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => void exportVersion(project.id, 'zh')}>译本 1 · 网页版</DropdownMenuItem>
                {variants.map(item => (
                  <DropdownMenuItem key={item.id} onSelect={() => void exportVersion(item.id, 'zh')}>译本 2 · {item.label}</DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="ghost" aria-label="更多"><MoreHorizontal /></Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-60">
                <DropdownMenuLabel>译本 2</DropdownMenuLabel>
                {SECOND_MODELS.map(option => (
                  <DropdownMenuItem key={option.model} disabled={busy || variants.some(v => v.label === option.label)} onSelect={() => void startModelVariant(option.model, option.label)}>
                    <Sparkles className="h-4 w-4" /> 用 {option.label} 再翻一版
                  </DropdownMenuItem>
                ))}
                <DropdownMenuItem disabled={busy || claudeRunning || claudeWaiting} onSelect={() => void startClaude()}>
                  <Bot className="h-4 w-4" /> {project.claude_run_id ? '重新交给 Claude' : '交给 Claude（four-step-translate）'}
                </DropdownMenuItem>
                {run && (
                  <DropdownMenuItem onSelect={() => setDrawer({ kind: 'claude', run })}>
                    <Bot className="h-4 w-4" /> 看 Claude 的对话
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to={`/document/${project.id}`}>旧版编辑器（单段重译、质量报告）</Link>
                </DropdownMenuItem>
                {project.original_url && (
                  <DropdownMenuItem asChild>
                    <a href={project.original_url} target="_blank" rel="noreferrer"><ExternalLink className="h-4 w-4" /> 原文链接</a>
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {(webWaitingTerms || claudeWaiting || claudeNote || project.status.error) && (
          <div className="mt-2 flex flex-col gap-1.5">
            {webWaitingTerms && (
              <Banner tone="wait" action="去确认" onAction={() => setDrawer({ kind: 'terms', projectId: project.id, jobId: project.status.run_id! })}>
                网页版在等你确认术语，过一会儿会自动采用建议。
              </Banner>
            )}
            {claudeWaiting && run && (
              <Banner tone="wait" action="去回答" onAction={() => setDrawer({ kind: 'claude', run })}>Claude 在问你问题。</Banner>
            )}
            {claudeNote && (
              <Banner
                tone="info"
                action={variants.some(v => v.label === 'argon') ? undefined : '改用 argon 再翻一版'}
                onAction={() => void startModelVariant('gemini-official-argon', 'argon')}
                secondary={run ? { label: '看 Claude 说了什么', onClick: () => setDrawer({ kind: 'claude', run }) } : undefined}
              >
                {claudeNote}
              </Banner>
            )}
            {project.status.error && <Banner tone="error">网页版出错了：{project.status.error}</Banner>}
          </div>
        )}

        {isMobile && (
          <div className="mt-2 grid grid-cols-3 rounded-lg bg-bg-tertiary p-0.5 text-sm" role="tablist" aria-label="切换栏">
            {PANES.map(id => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={mobilePane === id}
                onClick={() => setMobilePane(id)}
                className={cn('rounded-md py-1', mobilePane === id ? 'bg-white text-text-primary shadow-sm' : 'text-text-muted')}
              >
                {columns[id].title}
              </button>
            ))}
          </div>
        )}
      </header>

      {!variant && (!isMobile || mobilePane === 'alt') && !collapsed.alt && (
        <SecondVersionPrompt busy={busy} claudeActive={Boolean(claudeRunning || claudeWaiting)} onModel={startModelVariant} onClaude={startClaude} />
      )}

      <PaneGrid rows={rows} columns={columns} collapsed={collapsed} onToggle={toggle} mobilePane={isMobile ? mobilePane : null} />

      <TrackDrawer state={drawer} mainId={project.id} onClose={() => { setDrawer(null); void refresh(); void claudeRun.refetch(); }} />
    </div>
  );
}

function Banner({ tone, children, action, onAction, secondary }: {
  tone: 'wait' | 'info' | 'error';
  children: React.ReactNode;
  action?: string;
  onAction?: () => void;
  secondary?: { label: string; onClick: () => void };
}) {
  const styles = { wait: 'border-warning/30 bg-warning-light', info: 'border-info/25 bg-info-light', error: 'border-error/30 bg-error-light' }[tone];
  return (
    <div className={cn('flex flex-wrap items-center gap-2 rounded-lg border px-3 py-1.5 text-sm text-text-primary', styles)}>
      <AlertCircle className="h-4 w-4 shrink-0 text-text-secondary" />
      <span className="min-w-0 flex-1">{children}</span>
      {secondary && <Button size="sm" variant="ghost" onClick={secondary.onClick}>{secondary.label}</Button>}
      {action && <Button size="sm" variant="outline" onClick={onAction}>{action}</Button>}
    </div>
  );
}

function SecondVersionPrompt({ busy, claudeActive, onModel, onClaude }: {
  busy: boolean;
  claudeActive: boolean;
  onModel: (model: string, label: string) => void;
  onClaude: () => void;
}) {
  if (claudeActive) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border-subtle bg-bg-tertiary/60 px-4 py-2 text-sm md:px-6">
      <span className="text-text-secondary">还没有译本 2：</span>
      {SECOND_MODELS.slice(0, 1).map(option => (
        <Button key={option.model} size="sm" variant="outline" disabled={busy} onClick={() => onModel(option.model, option.label)}>
          <Sparkles /> 用 {option.label} 再翻一版
        </Button>
      ))}
      <Button size="sm" variant="ghost" disabled={busy} onClick={onClaude}><Bot /> 交给 Claude</Button>
      <span className="text-xs text-text-muted">付费文章 Claude 通常不肯全文翻译</span>
    </div>
  );
}
