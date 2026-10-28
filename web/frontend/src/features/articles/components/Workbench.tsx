import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Plus, RefreshCw, Star } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { harnessLabel } from '@/features/skills/harness';
import { skillsApi } from '@/features/skills/api';
import { isUnauthorized } from '@/features/skills/hooks';
import type { RunMeta } from '@/features/skills/types';
import { articlesApi, downloadText } from '../api';
import { articleKeys, useClaudeRun, useWorkbench } from '../hooks';
import { saveAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { AlignmentTooLow, importClaudeTrack, startClaudeTrack } from '../lib/claude';
import { flushEdits, unsavedEdits } from '../lib/edits';
import { loadCollapsed, PANES, saveCollapsed, togglePane, type Collapsed } from '../lib/panes';
import { sectionsWithMissing } from '../lib/tracks';
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
import { IconAction, VersionHeader, VersionName } from './VersionHeader';
import { VersionTabs } from './VersionTabs';
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
  const { project, rows } = data;
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
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

  const claudeRun = useClaudeRun(project.claude_run_id);
  const run = claudeRun.data;
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
      const result = await importClaudeTrack(project.id, target, force);
      toast.success(`${harnessLabel(target.harness)} 译文已导入：对上 ${result.aligned} 段`);
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
    if (data.variants.some(variant => variant.import?.run_id === run.id)) return;
    importTried.current = run.id;
    void Promise.resolve().then(() => importRun(run, false)); // 异步调用，effect 里不直接 setState
  }, [run, data.variants, importRun]);

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

  const continueTranslation = async (version: VersionView) => {
    try {
      if (version.source === 'web' && !rows.some(row => row.web)) {
        await articlesApi.startWorkflow(project.id);
        toast.success('网页版开始翻译');
      } else {
        const sections = sectionsWithMissing(rows, version.text);
        if (!sections.length) return;
        const names = sections.map(section => `「${section.title}」`).join('、');
        if (!window.confirm(`重译缺译段落所在的 ${sections.length} 章：${names}\n\n这几章里已有的译文（包括你改过的）会被新译文替换，其他章节不动。继续？`)) return;
        await articlesApi.startWorkflow(version.id, { model: version.fillModel, autoAcceptTerms: true, sectionIds: sections.map(section => section.id) });
        toast.success(`开始重译 ${sections.length} 章`);
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
    try {
      if (project.claude_run_id) {
        // 防止停下来的半成品被当成结果导入
        importTried.current = project.claude_run_id;
        const stopped = await skillsApi.stop(project.claude_run_id);
        queryClient.setQueryData(articleKeys.claudeRun(stopped.id), stopped);
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
      toast.success(`已交给 ${harnessLabel(choice.harness)}；它需要你确认时这里会提示`);
      await refresh();
      return true;
    } catch (error) {
      toast.error(isUnauthorized(error) ? '先去 Agent 页登录一次（只需一次）' : error instanceof Error ? error.message : '没能交出去');
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
      await articlesApi.setPrimary(project.id, version.id);
      queryClient.setQueryData<WorkbenchData>(articleKeys.workbench(project.id), current => current && {
        ...current, project: { ...current.project, primary_target: version.id, primary: version.id },
      });
      setCompareId(previous);
      toast.success(`主译本改为 ${version.name}`);
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
    else if (action.kind === 'force-import' && run) void importRun(run, true);
  };

  const menuFor = (version: VersionView): MenuItem[] => [
    ...(version.pending ? [] : [{ label: '看我改了什么', onSelect: () => setChanges({ projectId: project.id, target: version.id, label: version.name, title }) }]),
    ...(version.harness && run && (run.harness ?? 'claude') === version.harness
      ? [{ label: `看 ${version.name} 的对话`, onSelect: () => setDrawer({ kind: 'claude', run }) }] : []),
  ];

  const retranslate = (version: VersionView) => version.translate === 'retranslate' && version.harness ? (
    <RetranslatePopover projectId={project.id} version={version} stopping={stopping} busy={busy}
      onConfirm={model => startAgent({ harness: version.harness!, model })}>
      <IconAction label="重新翻译"><RefreshCw className="h-4 w-4" /></IconAction>
    </RetranslatePopover>
  ) : null;

  const placeholder = (version: VersionView) =>
    version.pending ? '译文还没出来' : version.tone === 'busy' ? '翻译中…' : '还没有译文，可以直接写';

  const columns: Record<PaneId, PaneColumn> = {
    source: {
      id: 'source',
      title: '英文',
      header: <VersionHeader eyebrow="原文" title={<VersionName english>English</VersionName>}
        line={<p className="mt-1.5 text-[12px] text-text-muted">{words.toLocaleString('en-US')} 词</p>} />,
    },
    main: {
      id: 'main',
      title: '主译本',
      primary: true,
      versionKey: primary.id,
      tone: primary.tone,
      readOnly: primary.readOnly,
      header: <VersionHeader primary eyebrow="主译本" title={<VersionName>{primary.name}</VersionName>}
        line={<StatusLine version={primary} onAction={action => onAction(primary, action)} />}
        actions={<>{retranslate(primary)}<ColumnMenu label="主译本的更多操作" items={menuFor(primary)} /></>} />,
      text: primary.text,
      save: (row, text) => save(primary.id, row, text),
      placeholder: placeholder(primary),
      adopt: compare && !compare.pending ? { label: compare.name, text: compare.text } : undefined,
    },
    compare: compare ? {
      id: 'compare',
      title: '对照',
      versionKey: compare.id,
      tone: compare.tone,
      readOnly: compare.readOnly || compare.pending,
      header: <VersionHeader eyebrow="对照"
        title={<VersionTabs versions={others} value={compare.id} onChange={id => void switchCompare(id)} forceMenu={isMobile}
          add={addable.length ? (
            <AddAgentPopover options={addable} stopping={stopping} busy={busy} onConfirm={startAgent}>
              <button type="button" aria-label="用 Agent 再翻一版" title="用 Agent 再翻一版"
                className="inline-flex items-center rounded-full px-2.5 py-1 text-primary-700 hover:bg-white/70"><Plus className="h-3.5 w-3.5" /></button>
            </AddAgentPopover>
          ) : null} />}
        line={<StatusLine version={compare} onAction={action => onAction(compare, action)} />}
        actions={<>
          {retranslate(compare)}
          {!compare.pending && (
            <button type="button" onClick={() => void makePrimary(compare)}
              className="inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-[12.5px] text-primary-700 hover:bg-primary-50">
              <Star className="h-3.5 w-3.5" />设为主译本
            </button>
          )}
          <ColumnMenu label="对照的更多操作" items={menuFor(compare)} />
        </>} />,
      text: compare.text,
      save: (row, text) => save(compare.id, row, text),
      placeholder: placeholder(compare),
      adopt: { label: primary.name, text: primary.text },
    } : {
      id: 'compare',
      title: '对照',
      header: <VersionHeader eyebrow="对照" title={<VersionName>还没有别的版本</VersionName>}
        line={<p className="mt-1.5 text-[12px] text-text-muted">用 Agent 翻一版，就能左右对照</p>} />,
      text: () => null,
      save: async () => undefined,
      readOnly: true,
      empty: <CompareEmpty options={addable} stopping={stopping} busy={busy} onStart={startAgent} />,
    },
  };

  const markRow = data.reading_mark ? rows.find(row => row.key === data.reading_mark?.key) : undefined;
  const markText = data.reading_mark ? (primary.text(markRow ?? rows[0]) || markRow?.source || '已标记的位置') : null;
  const exportItems = [
    { label: '英文原文', onSelect: () => void exportVersion(project.id, 'en') },
    ...versions.filter(version => !version.pending).map(version => ({
      label: `${version.name}${version.model ? `（${version.model}）` : ''}${version.id === primary.id ? ' · 主译本' : ''}`,
      onSelect: () => void exportVersion(version.id, 'zh'),
    })),
  ];

  return (
    <div className="flex h-full min-h-0 flex-col bg-bg-primary">
      <WorkbenchTopBar title={title} original={title !== project.title ? project.title : null}
        onShowList={onShowList} onBack={() => navigate('/articles')}
        save={<SaveStatus saving={saving} onSave={() => void saveNow()} />}
        mark={markText} onJump={() => setReadingJump(n => n + 1)} onClearMark={() => void markReading(null)} markBusy={markBusy}
        onExportPrimary={() => void exportVersion(primary.id, 'zh')} exportItems={exportItems}
        legacyHref={`/document/${project.id}`} originalUrl={project.original_url} />

      {isMobile && (
        <div className="mx-4 mb-2 grid grid-cols-3 rounded-full bg-[#f5eff1] p-[3px] text-[13px]" role="tablist" aria-label="切换栏">
          {PANES.map(id => (
            <button key={id} type="button" role="tab" aria-selected={mobilePane === id} onClick={() => setMobilePane(id)}
              className={cn('rounded-full py-1', mobilePane === id ? 'bg-white text-text-primary shadow-sm' : 'text-text-muted')}>
              {columns[id].title}
            </button>
          ))}
        </div>
      )}

      <PaneGrid rows={rows} columns={columns} collapsed={collapsed} onToggle={toggle} mobilePane={isMobile ? mobilePane : null}
        readingKey={data.reading_mark?.key} markBusy={markBusy} onMark={key => void markReading(key)} jump={readingJump} />

      <TrackDrawer state={drawer} mainId={project.id} onClose={() => { setDrawer(null); void refresh(); void claudeRun.refetch(); }} />
      <ChangesDrawer state={changes} onClose={() => setChanges(null)} />
    </div>
  );
}
