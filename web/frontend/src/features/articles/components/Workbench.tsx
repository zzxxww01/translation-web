import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { AlertCircle, ArrowLeft, Bookmark, Bot, Download, ExternalLink, FileDiff, MoreHorizontal, PanelLeft, Play, Save, X } from 'lucide-react';
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
import { harnessLabel, type Harness } from '@/features/skills/harness';
import { isUnauthorized } from '@/features/skills/hooks';
import { articlesApi, downloadText, HUMAN_EDITS_URL } from '../api';
import { articleKeys, useClaudeRun, useWorkbench } from '../hooks';
import { importClaudeTrack, NoClaudeOutput, startClaudeTrack } from '../lib/claude';
import { ARTICLE_HARNESSES } from '../lib/agentOptions';
import { flushEdits, unsavedEdits, usePaneSaveState } from '../lib/edits';
import { loadCollapsed, PANES, saveCollapsed, togglePane, type Collapsed } from '../lib/panes';
import { canFillMissing, countFilled, SECOND_MODELS, sectionsWithMissing, TERMS_STEP, trackSummary } from '../lib/tracks';
import type { PaneId, Workbench as WorkbenchData, WorkbenchRow, WorkbenchVariant } from '../types';
import { ChangesDrawer, type ChangesTarget } from './ChangesDrawer';
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

const clock = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });

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
  return <WorkbenchView key={projectId} data={query.data} onShowList={onShowList} />;
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
  const [changes, setChanges] = useState<ChangesTarget | null>(null);
  const [claudeNote, setClaudeNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [markBusy, setMarkBusy] = useState(false);
  const [readingJump, setReadingJump] = useState(0);
  const markLock = useRef(false);
  const importTried = useRef<string | null>(null);

  const variant: WorkbenchVariant | null = variants.find(v => v.id === variantId) ?? variants[0] ?? null;
  const claudeRun = useClaudeRun(project.claude_run_id);
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

  // Agent 任务做完了还没导入：自动取回 zh.md 导入（每个任务只自动试一次）。在等你确认时不算做完
  const run = claudeRun.data;
  useEffect(() => {
    if (!run || run.status !== 'idle' || run.awaiting_reply || importTried.current === run.id) return;
    if (variants.some(v => v.import?.run_id === run.id)) return;
    importTried.current = run.id;
    importClaudeTrack(project.id, run.id, run.harness ?? 'claude')
      .then(result => {
        toast.success(`${harnessLabel(run.harness)} 译文已导入：对上 ${result.aligned} 段`);
        setClaudeNote(null);
        return refresh();
      })
      .catch(error => setClaudeNote(error instanceof NoClaudeOutput ? `${harnessLabel(run.harness)} ${error.message}` : `译文导入失败：${error.message}`));
  }, [run, variants, project.id, refresh]);

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

  const markReading = async (key: string | null) => {
    if (markLock.current) return;
    markLock.current = true;
    setMarkBusy(true);
    try {
      await queryClient.cancelQueries({ queryKey: articleKeys.workbench(project.id) });
      const result = await articlesApi.setReadingMark(project.id, key);
      queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
        ...current, reading_mark: result.reading_mark,
      });
      toast.success(key ? '已标记：看到这里' : '已清除阅读标记');
    } catch (error) {
      toast.error(`阅读标记没保存上：${error instanceof Error ? error.message : '请重试'}`);
    } finally {
      markLock.current = false;
      setMarkBusy(false);
    }
  };

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

  /** 手动保存：改动本来就自动保存，这里只是让正在改的那段立刻存下，并确认都存好了 */
  const saveNow = useCallback(async () => {
    setSaving(true);
    try {
      if (await flushEdits()) toast.success('已保存');
      else toast.error('有段落没保存上（标红的那几段），点它旁边的「重试」');
    } finally {
      setSaving(false);
    }
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        void saveNow();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [saveNow]);

  const startWeb = async () => {
    setBusy(true);
    try {
      await articlesApi.startWorkflow(project.id);
      toast.success('网页版开始翻译');
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能开始');
    } finally {
      setBusy(false);
    }
  };

  const fillMissing = async (target: string, text: (row: WorkbenchRow) => string | null, model?: string) => {
    const sections = sectionsWithMissing(rows, text);
    if (!sections.length) return;
    const names = sections.map(section => `「${section.title}」`).join('、');
    if (!window.confirm(`重译缺译段落所在的 ${sections.length} 章：${names}

这几章里已有的译文（包括你改过的）会被新译文替换，其他章节不动。继续？`)) return;
    try {
      await articlesApi.startWorkflow(target, { model, autoAcceptTerms: true, sectionIds: sections.map(section => section.id) });
      toast.success(`开始重译 ${sections.length} 章`);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能开始补译');
    }
  };

  const startClaude = async (harness: Harness = 'codex') => {
    setBusy(true);
    try {
      await startClaudeTrack(project.id, harness, title);
      setClaudeNote(null);
      importTried.current = null;
      toast.success(`已交给 ${harnessLabel(harness)}；它需要你确认时这里会提示`);
      await refresh();
    } catch (error) {
      toast.error(isUnauthorized(error) ? '先去 Agent 页登录一次（只需一次）' : error instanceof Error ? error.message : '没能交出去');
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
  const webNotStarted = !project.status.active && webFilled.done === 0;

  const columns = useMemo<Record<PaneId, PaneColumn>>(() => {
    const altLabel = variant ? `译本 2 · ${variant.label}` : '译本 2';
    return {
      source: {
        id: 'source',
        title: '英文',
        header: (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-secondary">英文</span>
            <IconButton title="导出英文原文" onClick={() => void exportVersion(project.id, 'en')}><Download className="h-3.5 w-3.5" /></IconButton>
          </div>
        ),
      },
      web: {
        id: 'web',
        title: '译本 1',
        header: (
          <VersionHeader
            pane="web"
            label={<span className="text-sm font-medium text-text-secondary">译本 1 · 网页版</span>}
            summary={webSummary.text}
            summaryTitle={project.status.current_step ?? undefined}
            start={webNotStarted ? { label: '开始翻译', onClick: () => void startWeb(), disabled: busy } : null}
            onFill={canFillMissing(project.status, webFilled) ? () => void fillMissing(project.id, row => row.web) : undefined}
            onExport={() => void exportVersion(project.id, 'zh')}
            onChanges={() => setChanges({ projectId: project.id, target: project.id, label: '译本 1 · 网页版', title })}
          />
        ),
        text: row => row.web,
        save: (row, text) => save(project.id, row, text),
        placeholder: project.status.active ? '翻译中…' : '还没有译文，可以直接写',
        adopt: variant ? { label: variant.label, text: row => row.alt[variant.id] ?? null } : undefined,
      },
      alt: {
        id: 'alt',
        title: '译本 2',
        header: variant ? (
          <VersionHeader
            pane="alt"
            label={variants.length > 1 ? (
              <select
                aria-label="选择译本 2"
                value={variant.id}
                onChange={event => setVariantId(event.target.value)}
                className="rounded-md border border-border-subtle bg-white px-1.5 py-0.5 text-sm text-text-secondary"
              >
                {variants.map(item => <option key={item.id} value={item.id}>译本 2 · {item.label}</option>)}
              </select>
            ) : (
              <span className="text-sm font-medium text-text-secondary">{altLabel}</span>
            )}
            summary={altSummary?.text}
            summaryTitle={variant.status.current_step ?? undefined}
            onFill={variant.kind === 'model' && altFilled && canFillMissing(variant.status, altFilled)
              ? () => void fillMissing(variant.id, row => row.alt[variant.id] ?? null, SECOND_MODELS.find(option => option.label === variant.label)?.model)
              : undefined}
            onExport={() => void exportVersion(variant.id, 'zh')}
            onChanges={() => setChanges({ projectId: project.id, target: variant.id, label: altLabel, title })}
          />
        ) : (
          <span className="text-sm font-medium text-text-secondary">{altLabel}</span>
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
    // exportVersion / startWeb 只依赖下面这些，跟着它们变
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project, variant, variants, webSummary.text, altSummary?.text, save, busy, webNotStarted, title]);

  const claudeRunning = run?.status === 'running';
  // 提问挂着（waiting），或者一轮结束时说了在等确认（Codex 都是这种）
  const claudeWaiting = run?.status === 'waiting' || Boolean(run?.status === 'idle' && run.awaiting_reply);
  const agentLabel = harnessLabel(run?.harness);
  const runImported = Boolean(run && variants.some(v => v.import?.run_id === run.id));
  // 这篇有 Agent 任务，但浏览器还没登录 Agent 页：说一声，不然这一路像不存在
  const claudeNeedsLogin = Boolean(project.claude_run_id) && isUnauthorized(claudeRun.error);
  const autoReplyAt = run?.auto_reply_at ? clock.format(run.auto_reply_at * 1000) : null;

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
            {(claudeRunning || claudeWaiting) && !runImported && (
              <StatusChip label={agentLabel} text={claudeWaiting ? '在等你确认' : '翻译中'} tone={claudeWaiting ? 'wait' : 'busy'} />
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button size="sm" variant="outline" disabled={saving} onClick={() => void saveNow()} title="Ctrl/⌘ + S。改动本来就会自动保存，这里是立刻存下">
              <Save /> {saving ? '保存中…' : '保存'}
            </Button>
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
                <DropdownMenuLabel>译本 2（Agent）</DropdownMenuLabel>
                {ARTICLE_HARNESSES.map(item => (
                  <DropdownMenuItem key={item.id} disabled={busy || claudeRunning || claudeWaiting} onSelect={() => void startClaude(item.id)}>
                    <Bot className="h-4 w-4" /> 交给 {item.label}（four-step-translate）
                  </DropdownMenuItem>
                ))}
                {run && (
                  <DropdownMenuItem onSelect={() => setDrawer({ kind: 'claude', run })}>
                    <Bot className="h-4 w-4" /> 看 {agentLabel} 的对话
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <a href={HUMAN_EDITS_URL}><FileDiff className="h-4 w-4" /> 下载全部文章的人工改动</a>
                </DropdownMenuItem>
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

        {(webWaitingTerms || claudeWaiting || claudeNote || claudeNeedsLogin || project.status.error) && (
          <div className="mt-2 flex flex-col gap-1.5">
            {webWaitingTerms && (
              <Banner tone="wait" action="去确认" onAction={() => setDrawer({ kind: 'terms', projectId: project.id, jobId: project.status.run_id! })}>
                网页版在等你确认术语，10 分钟内不确认会自动采用建议。
              </Banner>
            )}
            {claudeWaiting && run && (
              <Banner tone="wait" action="去确认" onAction={() => setDrawer({ kind: 'claude', run })}>
                {agentLabel} 在等你确认（比如术语表）{autoReplyAt ? `，${autoReplyAt} 前不回复就自动按它的建议继续` : ''}。
              </Banner>
            )}
            {claudeNote && (
              <Banner
                tone="info"
                action={run?.harness !== 'codex' ? '改用 Codex 翻' : undefined}
                onAction={() => void startClaude('codex')}
                secondary={run ? { label: `看 ${agentLabel} 说了什么`, onClick: () => setDrawer({ kind: 'claude', run }) } : undefined}
              >
                {claudeNote}
              </Banner>
            )}
            {claudeNeedsLogin && (
              <Banner tone="info" action="去登录" onAction={() => navigate('/skills')}>
                这篇交给过 Agent，要先登录 Agent 页（一次即可）才能看进度和回复。
              </Banner>
            )}
            {project.status.error && <Banner tone="error">网页版出错了：{project.status.error}</Banner>}
          </div>
        )}

        <div className="mt-2 flex items-center gap-2 text-xs text-text-muted">
          <Bookmark className="h-3.5 w-3.5 shrink-0" />
          {data.reading_mark ? <>
            <span className="min-w-0 flex-1 truncate">看到这里：{rows.find(row => row.key === data.reading_mark?.key)?.web || rows.find(row => row.key === data.reading_mark?.key)?.source || '已标记的位置'}</span>
            <button type="button" onClick={() => setReadingJump(n => n + 1)} className="shrink-0 rounded px-2 py-1 text-primary-700 hover:bg-primary-50">继续阅读</button>
            <button type="button" aria-label="清除阅读标记" disabled={markBusy} onClick={() => void markReading(null)} className="rounded p-1 hover:bg-bg-hover disabled:opacity-40"><X className="h-3.5 w-3.5" /></button>
          </> : <span>在段落上边缘点“看到这里”，再点一次可取消</span>}
          {markBusy && <span role="status">保存标记中…</span>}
        </div>
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
        <SecondVersionPrompt busy={busy} agentActive={Boolean(claudeRunning || claudeWaiting)} onStart={startClaude} />
      )}

      <PaneGrid rows={rows} columns={columns} collapsed={collapsed} onToggle={toggle} mobilePane={isMobile ? mobilePane : null}
        readingKey={data.reading_mark?.key} markBusy={markBusy} onMark={key => void markReading(key)} jump={readingJump} />

      <TrackDrawer state={drawer} mainId={project.id} onClose={() => { setDrawer(null); void refresh(); void claudeRun.refetch(); }} />
      <ChangesDrawer state={changes} onClose={() => setChanges(null)} />
    </div>
  );
}

function IconButton({ title, onClick, children }: { title: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" title={title} aria-label={title} onClick={onClick} className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary">
      {children}
    </button>
  );
}

/** 中文栏的栏头：栏名、进度、（开始翻译 / 补译）、保存状态、改动、导出 */
function VersionHeader({ pane, label, summary, summaryTitle, start, onFill, onExport, onChanges }: {
  pane: 'web' | 'alt';
  label: ReactNode;
  summary?: string;
  summaryTitle?: string;
  start?: { label: string; onClick: () => void; disabled?: boolean } | null;
  onFill?: () => void;
  onExport: () => void;
  onChanges: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      {label}
      {summary && <span className="text-xs text-text-muted" title={summaryTitle}>{summary}</span>}
      {start && (
        <button type="button" disabled={start.disabled} onClick={start.onClick} className="inline-flex items-center gap-1 rounded-md px-1.5 text-xs text-primary-700 hover:bg-primary-50 disabled:opacity-50">
          <Play className="h-3 w-3" /> {start.label}
        </button>
      )}
      {onFill && <button type="button" onClick={onFill} className="rounded-md px-1.5 text-xs text-primary-700 hover:bg-primary-50">补译</button>}
      <span className="flex-1" />
      <SaveState pane={pane} />
      <IconButton title="看你改了什么" onClick={onChanges}><FileDiff className="h-3.5 w-3.5" /></IconButton>
      <IconButton title="导出这一版" onClick={onExport}><Download className="h-3.5 w-3.5" /></IconButton>
    </div>
  );
}

/** 这一栏的保存状态（自动保存和手动保存一样，只说明存没存下） */
function SaveState({ pane }: { pane: 'web' | 'alt' }) {
  const state = usePaneSaveState(pane);
  if (state.failed) return <span className="text-xs text-error">{state.failed} 段没保存上</span>;
  if (state.busy) return <span className="text-xs text-text-muted">保存中…</span>;
  if (state.savedAt) return <span className="text-xs text-text-muted">已保存 {clock.format(state.savedAt)}</span>;
  return null;
}

function Banner({ tone, children, action, onAction, secondary }: {
  tone: 'wait' | 'info' | 'error';
  children: ReactNode;
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

function SecondVersionPrompt({ busy, agentActive, onStart }: {
  busy: boolean;
  agentActive: boolean;
  onStart: (harness: Harness) => void;
}) {
  if (agentActive) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border-subtle bg-bg-tertiary/60 px-4 py-2 text-sm md:px-6">
      <span className="text-text-secondary">还没有译本 2：</span>
      {ARTICLE_HARNESSES.map(item => (
        <Button key={item.id} size="sm" variant={item.id === 'codex' ? 'outline' : 'ghost'} disabled={busy} onClick={() => onStart(item.id)}>
          <Bot /> 交给 {item.label}
        </Button>
      ))}
      <span className="text-xs text-text-muted">都跑 four-step-translate；付费文章 Claude 通常不肯全文翻译</span>
    </div>
  );
}
