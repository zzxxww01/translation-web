import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Minimize2, RefreshCw, Star } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { harnessLabel } from '@/features/skills/harness';
import { skillsApi } from '@/features/skills/api';
import { ApiErrorWrapper } from '@/shared/api/client';
import { isUnauthorized } from '@/features/skills/hooks';
import type { RunMeta } from '@/features/skills/types';
import { articlesApi, downloadText } from '../api';
import { articleKeys, useClaudeRun, useWorkbench } from '../hooks';
import { saveAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { AlignmentTooLow, importClaudeTrack, startClaudeTrack } from '../lib/claude';
import { flushEdits, unsavedEdits } from '../lib/edits';
import { editHistory, undoShortcut } from '../lib/history';
import { loadCollapsed, PANES, saveCollapsed, togglePane, type Collapsed } from '../lib/panes';
import { sectionsWithMissing } from '../lib/tracks';
import { FOCUS_RING, MEASURE, onTabKeys, STROKE } from '../lib/ui';
import { buildVersions, defaultCompare, pickPrimary, runActive, type ImportProblem, type VersionAction, type VersionView } from '../lib/versions';
import type { PaneId, Workbench as WorkbenchData, WorkbenchRow } from '../types';
import { ChangesDrawer, type ChangesTarget } from './ChangesDrawer';
import { ColumnMenu, type MenuItem } from './ColumnMenu';
import { CompareEmpty } from './CompareEmpty';
import { PaneGrid, type PaneColumn } from './PaneGrid';
import { SaveStatus } from './SaveStatus';
import { StatusLine } from './StatusLine';
import { TrackDrawer, type DrawerState } from './TrackDrawer';
import { AddAgentPopover, RetranslatePopover } from './TranslatePopovers';
import { IconAction, PlainLine, VersionName } from './VersionHeader';
import { AddVersionButton, VersionTabs } from './VersionTabs';
import { WorkbenchTopBar } from './WorkbenchTopBar';

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

/** 焦点在输入框或弹框里：快捷键交给它们自己 */
function typingOrDialog(target: EventTarget | null): boolean {
  return target instanceof HTMLElement
    && (target.isContentEditable || Boolean(target.closest('input, textarea, select, [role="dialog"], [role="menu"]')));
}

/**
 * 沉浸模式：整屏只留三栏（顶部导航和顶栏都收起，导航靠 AppLayout 认 ?immersive=1）。
 * 进入时顺便请浏览器全屏；按 Esc 先退出浏览器全屏，再按一次（不在编辑时）退出沉浸模式。
 */
function useImmersive() {
  const [searchParams, setSearchParams] = useSearchParams();
  const immersive = searchParams.get('immersive') === '1';
  const setParam = useCallback((on: boolean) => setSearchParams(current => {
    const next = new URLSearchParams(current);
    if (on) next.set('immersive', '1');
    else next.delete('immersive');
    return next;
  }, { replace: true }), [setSearchParams]);
  const enter = useCallback(() => {
    setParam(true);
    // 不支持或被浏览器拒绝时，只是在窗口里铺满
    void document.documentElement.requestFullscreen?.()?.catch(() => undefined);
  }, [setParam]);
  const exit = useCallback(() => {
    setParam(false);
    if (document.fullscreenElement) void document.exitFullscreen().catch(() => undefined);
  }, [setParam]);

  useEffect(() => {
    if (!immersive) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.defaultPrevented || typingOrDialog(event.target)) return;
      if (document.body.querySelector('[data-radix-popper-content-wrapper], [role="dialog"]')) return; // 先关弹出层
      exit();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [immersive, exit]);

  // 离开工作台时把浏览器全屏也退掉
  useEffect(() => () => {
    if (document.fullscreenElement) void document.exitFullscreen().catch(() => undefined);
  }, []);

  return { immersive, enter, exit };
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
  // 只有一次都没读到才显示错误页；后台刷新失败时留着现有内容（编辑框和草稿不能丢）
  if (!query.data) {
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
  const { project, rows } = data;
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const { immersive, enter: enterImmersive, exit: exitImmersive } = useImmersive();
  const [collapsed, setCollapsed] = useState<Collapsed>(loadCollapsed);
  const [mobilePane, setMobilePane] = useState<PaneId>('main');
  const [compareId, setCompareId] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<DrawerState>(null);
  const [changes, setChanges] = useState<ChangesTarget | null>(null);
  const [importProblem, setImportProblem] = useState<ImportProblem | null>(null);
  const [busy, setBusy] = useState(false);
  const agentStartLock = useRef(false);
  const [saving, setSaving] = useState(false);
  const [markBusy, setMarkBusy] = useState(false);
  const [readingJump, setReadingJump] = useState(0);
  const markLock = useRef(false);
  const importTried = useRef<string | null>(null);
  /** 这个任务又跑过一轮：再次空闲时要重新导入（即使上次导入的就是它） */
  const reimport = useRef<string | null>(null);
  const forceLock = useRef(false);
  const [startError, setStartError] = useState<string | null>(null);

  const claudeRun = useClaudeRun(project.claude_run_id);
  const run = claudeRun.data ?? undefined;
  const needsLogin = Boolean(project.claude_run_id) && isUnauthorized(claudeRun.error);
  const { versions, addable } = useMemo(
    () => buildVersions({ data, run, needsLogin, importProblem }), [data, run, needsLogin, importProblem]);
  const primary = pickPrimary(versions, project.primary);
  const others = versions.filter(version => version.id !== primary.id);
  const compare = others.find(version => version.id === compareId) ?? defaultCompare(versions, primary, run);
  const title = project.title_translation || primary.variant?.title_translation || project.title;
  const stopping = run && runActive(run) ? harnessLabel(run.harness) : null;
  const words = useMemo(() => rows.reduce(
    (count, row) => (row.kind === 'image' ? count : count + (row.source.match(/[A-Za-z0-9][A-Za-z0-9'’.-]*/g)?.length ?? 0)), 0), [rows]);
  const refresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: articleKeys.workbench(project.id) }),
    [queryClient, project.id],
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

  const importRun = useCallback(async (target: RunMeta, force: boolean) => {
    try {
      await importClaudeTrack(project.id, target, force);
      setImportProblem(null);
      await refresh();
    } catch (error) {
      setImportProblem({ runId: target.id, alignment: error instanceof AlignmentTooLow,
        message: error instanceof Error ? error.message : '导入失败' });
    }
  }, [project.id, refresh]);

  // Agent 一轮结束、不是在等你确认、还没导入：自动取回 zh.md 导入（每个任务只自动试一次）
  useEffect(() => {
    if (!run || run.status !== 'idle' || run.awaiting_reply || importTried.current === run.id) return;
    if (reimport.current !== run.id && data.variants.some(variant => variant.import?.run_id === run.id)) return;
    importTried.current = run.id;
    reimport.current = null;
    void Promise.resolve().then(() => importRun(run, false)); // 异步调用，effect 里不直接 setState
  }, [run, data.variants, importRun]);

  // 同一个任务又开始干活（继续对话）：上一次的导入结果作废，空闲后重新导入
  const runWorking = Boolean(run && (run.status === 'running' || run.status === 'waiting' || run.awaiting_reply));
  const workingId = runWorking ? run?.id : undefined;
  useEffect(() => {
    if (!workingId) return;
    importTried.current = null;
    reimport.current = workingId;
    void Promise.resolve().then(() => setImportProblem(current => (current?.runId === workingId ? null : current)));
  }, [workingId]);

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
        try {
          const result = await articlesApi.exportMarkdown(target, format, true);
          downloadText(result.filename, result.content);
        } catch (forced) {
          toast.error(forced instanceof Error ? forced.message : '导出失败');
        }
        return;
      }
      toast.error(error instanceof Error ? error.message : '导出失败');
    }
  };

  /** 手动保存：改动本来就自动保存，这里只是让正在改的那段立刻存下，并确认都存好了 */
  const saveNow = useCallback(async () => {
    setSaving(true);
    try {
      await flushEdits(); // 结果（已保存 / N 段没保存上）由顶栏 SaveStatus 显示
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

  // 不在编辑框里按撤销/重做：改回页面上最近改过的那一段（在编辑框里由编辑框自己处理）
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const shortcut = undoShortcut(event);
      if (!shortcut || event.defaultPrevented || typingOrDialog(event.target)) return;
      if (shortcut === 'undo' ? editHistory.undoLatest() : editHistory.redoLatest()) event.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const continueTranslation = async (version: VersionView) => {
    try {
      if (version.source === 'web' && !rows.some(row => row.web)) {
        await articlesApi.startWorkflow(project.id);
      } else {
        const sections = sectionsWithMissing(rows, version.text);
        if (!sections.length) return;
        const names = sections.map(section => `「${section.title}」`).join('、');
        if (!window.confirm(`重译缺译段落所在的 ${sections.length} 章：${names}\n\n这几章里已有的译文（包括你改过的）会被新译文替换，其他章节不动。继续？`)) return;
        await articlesApi.startWorkflow(version.id, { model: version.fillModel, autoAcceptTerms: true, sectionIds: sections.map(section => section.id) });
      }
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能开始');
    }
  };

  /** 交给 Agent：有旧任务先停干净再开新的。成功返回 true（弹框据此关掉）。 */
  const startAgent = async (choice: AgentChoice): Promise<boolean> => {
    if (agentStartLock.current) return false;
    agentStartLock.current = true;
    setBusy(true);
    setStartError(null);
    try {
      if (project.claude_run_id) {
        // 防止停下来的半成品被当成结果导入
        importTried.current = project.claude_run_id;
        try {
          const stopped = await skillsApi.stop(project.claude_run_id);
          queryClient.setQueryData(articleKeys.claudeRun(stopped.id), stopped);
        } catch (error) {
          // 那段 Agent 对话已被删掉：没有东西可停，直接开新的
          if (!(error instanceof ApiErrorWrapper && error.status === 404)) throw error;
        }
      }
      const nextRun = await startClaudeTrack(project.id, choice, title);
      saveAgentChoice(choice);
      queryClient.setQueryData(articleKeys.claudeRun(nextRun.id), nextRun);
      queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
        ...current, project: { ...current.project, claude_run_id: nextRun.id },
      });
      setImportProblem(null);
      importTried.current = null;
      const versionId = `${project.id}--${choice.harness}`;
      if (versionId !== primary.id) setCompareId(versionId);
      await refresh();
      return true;
    } catch (error) {
      // 弹框还开着，错误写在里面
      setStartError(isUnauthorized(error) ? '先去 Agent 页登录一次（只需一次）' : error instanceof Error ? error.message : '没能交出去');
      return false;
    } finally {
      agentStartLock.current = false;
      setBusy(false);
    }
  };

  const makePrimary = async (version: VersionView) => {
    if (!(await flushEdits())) {
      toast.error('有段落没保存上，先处理再换主译本');
      return;
    }
    const previous = primary.id;
    try {
      // 先停掉进行中的刷新，免得旧数据盖掉新选的主译本；服务器没存上就什么都不改
      await queryClient.cancelQueries({ queryKey: articleKeys.workbench(project.id) });
      await articlesApi.setPrimary(project.id, version.id);
      queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
        ...current, project: { ...current.project, primary_target: version.id, primary: version.id },
      });
      setCompareId(previous);
      // 文章列表里的进度跟着主译本走
      void queryClient.invalidateQueries({ queryKey: ['articles', 'library'] });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能设为主译本');
    }
  };

  const switchCompare = async (id: string) => {
    if (id === compare?.id) return;
    if (!(await flushEdits())) {
      toast.error('有段落没保存上，先处理再切换');
      return;
    }
    setCompareId(id);
  };

  const onAction = (version: VersionView, action: VersionAction) => {
    if (action.kind === 'confirm-terms') setDrawer({ kind: 'terms', projectId: version.id, jobId: action.jobId });
    else if (action.kind === 'open-run' && run) setDrawer({ kind: 'claude', run });
    else if (action.kind === 'continue') void continueTranslation(version);
    else if (action.kind === 'login') navigate('/skills');
    else if (action.kind === 'force-import' && run) {
      if (forceLock.current) return;
      forceLock.current = true;
      setImportProblem(null); // 状态行变成「正在导入」；失败时 importRun 会把问题写回来
      void importRun(run, true).finally(() => { forceLock.current = false; });
    }
  };

  const menuFor = (version: VersionView): MenuItem[] => [
    ...(version.pending ? [] : [{ label: '看我改了什么', onSelect: () => setChanges({ projectId: project.id, target: version.id, label: version.name, title }) }]),
    ...(version.harness && run && (run.harness ?? 'claude') === version.harness
      ? [{ label: `看 ${version.name} 的对话`, onSelect: () => setDrawer({ kind: 'claude', run }) }] : []),
  ];

  const retranslate = (version: VersionView) => version.translate === 'retranslate' && version.harness ? (
    <RetranslatePopover projectId={project.id} version={version} stopping={stopping} busy={busy}
      error={startError} onOpen={() => setStartError(null)} onConfirm={model => startAgent({ harness: version.harness!, model })}>
      <IconAction label="重新翻译" className="data-[state=open]:bg-ink-wash data-[state=open]:text-text-primary">
        <RefreshCw aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
      </IconAction>
    </RetranslatePopover>
  ) : null;

  const placeholder = (version: VersionView) => version.tone === 'busy' ? '翻译中…' : '还没有译文，可以直接写';
  /** 还没有译文的版本：整栏只说一句，不在每段重复 */
  const pendingNote = (version: VersionView) => version.pending
    ? <p className={cn(MEASURE, 'pt-1 text-[15px] text-text-muted [font-family:var(--font-display)]')}>译文还没出来</p> : undefined;
  /** 同一版整篇换过（重翻导入）时变：PaneGrid 只在这时淡入 */
  const contentKey = (version: VersionView) => version.pending ? 'pending' : version.variant?.import?.imported_at ?? '';

  const columns: Record<PaneId, PaneColumn> = {
    source: {
      id: 'source',
      title: '英文',
      header: { eyebrow: '原文', title: <VersionName english>English</VersionName>,
        line: <PlainLine>{words.toLocaleString('en-US')} 词</PlainLine> },
    },
    main: {
      id: 'main',
      title: '主译本',
      primary: true,
      versionKey: primary.id,
      contentKey: contentKey(primary),
      tone: primary.tone,
      readOnly: primary.readOnly,
      header: { primary: true, eyebrow: '主译本', title: <VersionName>{primary.name}</VersionName>,
        line: <StatusLine version={primary} onAction={action => onAction(primary, action)} />,
        actions: <>{retranslate(primary)}<ColumnMenu label="主译本的更多操作" items={menuFor(primary)} /></> },
      text: primary.text,
      save: (row, text) => save(primary.id, row, text),
      placeholder: placeholder(primary),
      empty: pendingNote(primary),
      adopt: compare && !compare.pending ? { label: compare.name, text: compare.text } : undefined,
    },
    compare: compare ? {
      id: 'compare',
      title: '对照',
      versionKey: compare.id,
      contentKey: contentKey(compare),
      tone: compare.tone,
      readOnly: compare.readOnly || compare.pending,
      header: { eyebrow: '对照',
        title: <VersionTabs versions={others} value={compare.id} onChange={id => void switchCompare(id)} forceMenu={isMobile} controls="pane-compare"
          add={addable.length ? (
            <AddAgentPopover options={addable} stopping={stopping} busy={busy} error={startError} onOpen={() => setStartError(null)} onConfirm={startAgent}>
              <AddVersionButton />
            </AddAgentPopover>
          ) : null} />,
        line: <StatusLine version={compare} onAction={action => onAction(compare, action)} />,
        actions: <>
          {retranslate(compare)}
          {!compare.pending && (
            <button type="button" onClick={() => void makePrimary(compare)}
              className={cn('mr-0.5 inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-lg px-2.5 text-[12.5px] font-medium text-primary-700 transition-colors hover:bg-primary-50', FOCUS_RING)}>
              <Star aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} />设为主译本
            </button>
          )}
          <ColumnMenu label="对照的更多操作" items={menuFor(compare)} />
        </> },
      text: compare.text,
      save: (row, text) => save(compare.id, row, text),
      placeholder: placeholder(compare),
      empty: pendingNote(compare),
      adopt: { label: primary.name, text: primary.text },
    } : {
      id: 'compare',
      title: '对照',
      header: { eyebrow: '对照', title: <VersionName>还没有别的版本</VersionName>,
        line: <PlainLine>用 Agent 翻一版，就能左右对照</PlainLine> },
      text: () => null,
      save: async () => undefined,
      readOnly: true,
      empty: <CompareEmpty options={addable} stopping={stopping} busy={busy} error={startError} onStart={startAgent} />,
    },
  };

  const markRow = data.reading_mark ? rows.find(row => row.key === data.reading_mark?.key) : undefined;
  // 标记的那一段已经不在了（文章重新导入过）：不显示标记，不拿别的段落顶替
  const markText = markRow ? (primary.text(markRow) || markRow.source) : null;
  const exportItems = [
    { label: '英文原文', onSelect: () => void exportVersion(project.id, 'en') },
    ...versions.filter(version => !version.pending).map(version => ({
      label: `${version.name}${version.model ? `（${version.model}）` : ''}${version.id === primary.id ? ' · 主译本' : ''}`,
      onSelect: () => void exportVersion(version.id, 'zh'),
    })),
  ];

  return (
    <div className="flex h-full min-h-0 flex-col bg-bg-primary">
      {!immersive && (
        <WorkbenchTopBar title={title} original={title !== project.title ? project.title : null}
          onShowList={onShowList} onBack={() => navigate('/articles')}
          save={<SaveStatus saving={saving} onSave={() => void saveNow()} compact={isMobile} />} compact={isMobile}
          mark={markText} onJump={() => setReadingJump(n => n + 1)} onClearMark={() => void markReading(null)} markBusy={markBusy}
          onExportPrimary={() => void exportVersion(primary.id, 'zh')} exportItems={exportItems}
          onImmersive={enterImmersive} legacyHref={`/document/${project.id}`} originalUrl={project.original_url} />
      )}

      {isMobile && (
        <div className={cn('mx-4 mb-3 grid grid-cols-3 gap-0.5 rounded-full bg-bg-inset p-[3px] text-[13px]', immersive && 'mt-3')} role="tablist" aria-label="切换栏">
          {PANES.map(id => (
            <button key={id} type="button" role="tab" data-tab-id={id} aria-selected={mobilePane === id} aria-controls={`pane-${id}`}
              tabIndex={mobilePane === id ? 0 : -1} onClick={() => setMobilePane(id)}
              onKeyDown={event => onTabKeys(event, PANES, mobilePane, id => setMobilePane(id as PaneId))}
              className={cn('h-8 rounded-full', FOCUS_RING, mobilePane === id ? 'bg-bg-secondary font-medium text-text-primary shadow-thumb' : 'text-text-muted')}>
              {columns[id].title}
            </button>
          ))}
        </div>
      )}

      <PaneGrid rows={rows} columns={columns} collapsed={collapsed} onToggle={toggle} mobilePane={isMobile ? mobilePane : null}
        readingKey={data.reading_mark?.key} markBusy={markBusy} onMark={key => void markReading(key)} jump={readingJump}
        immersive={immersive} corner={immersive ? (
          <IconAction label="退出沉浸模式" title="退出沉浸模式（Esc）" onClick={exitImmersive}>
            <Minimize2 aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
          </IconAction>
        ) : null} />

      <TrackDrawer state={drawer} mainId={project.id} onClose={() => { setDrawer(null); void refresh(); void claudeRun.refetch(); }} />
      <ChangesDrawer state={changes} onClose={() => setChanges(null)} />
    </div>
  );
}
