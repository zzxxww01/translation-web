import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, BookOpen, Globe2, Languages, Plus, Search, Star } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { ButtonExtended as Button } from '@/components/ui/button-extended';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { glossaryApi, type AddTermRequest, type BatchGlossaryRequest } from '@/features/confirmation/api/glossaryApi';
import type { GlossaryRecommendation, GlossaryTerm, TranslationStrategy } from '@/features/confirmation/types';
import {
  emptyEditor,
  normalizeTags,
  scopeLabel,
  toEditor,
  type EditingTerm,
  type GlossaryCenterProps,
  type GlossaryScope,
  type ListMode,
  type SortKey,
} from './types';
import { TermTable, GroupedTermView } from './components/TermTable';
import { TermEditor } from './components/TermEditor';
import { BatchActionsBar } from './components/BatchActionsBar';
import { RecommendationsList } from './components/RecommendationsList';

export function GlossaryCenter({ projectId, projectTitle, defaultScope = 'global', onBack }: GlossaryCenterProps) {
  const [activeScope, setActiveScope] = useState<GlossaryScope>(projectId ? defaultScope : 'global');
  const [projectTerms, setProjectTerms] = useState<GlossaryTerm[]>([]);
  const [globalTerms, setGlobalTerms] = useState<GlossaryTerm[]>([]);
  const [recommendations, setRecommendations] = useState<GlossaryRecommendation[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'disabled'>('active');
  const [strategyFilter, setStrategyFilter] = useState<'all' | TranslationStrategy>('all');
  const [tagFilter, setTagFilter] = useState('all');
  const [sortKey, setSortKey] = useState<SortKey>('updated_at');
  const [listMode, setListMode] = useState<ListMode>('table');
  const [selectedOriginals, setSelectedOriginals] = useState<string[]>([]);
  const [focusedOriginal, setFocusedOriginal] = useState<string | null>(null);
  const [editor, setEditor] = useState<EditingTerm>(emptyEditor);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [tagDraft, setTagDraft] = useState('');

  useEffect(() => {
    setActiveScope(projectId ? defaultScope : 'global');
  }, [defaultScope, projectId]);

  async function loadData() {
    setIsLoading(true);
    try {
      const requests: Promise<unknown>[] = [glossaryApi.getGlobalGlossary()];
      if (projectId) {
        requests.unshift(glossaryApi.getProjectGlossary(projectId));
        requests.push(glossaryApi.getProjectRecommendations(projectId));
      }
      const results = await Promise.all(requests);
      if (projectId) {
        const [projectGlossary, globalGlossary, recommendationData] = results as [
          { terms: GlossaryTerm[] },
          { terms: GlossaryTerm[] },
          { recommendations: GlossaryRecommendation[] },
        ];
        setProjectTerms(projectGlossary.terms);
        setGlobalTerms(globalGlossary.terms);
        setRecommendations(recommendationData.recommendations);
      } else {
        setProjectTerms([]);
        setGlobalTerms((results[0] as { terms: GlossaryTerm[] }).terms);
        setRecommendations([]);
      }
    } catch (error) {
      console.error('Failed to load glossary center:', error);
      toast.error('加载术语中心失败');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [projectId]);

  useEffect(() => {
    setSelectedOriginals([]);
    setFocusedOriginal(null);
    setIsCreating(false);
    setEditor(emptyEditor);
    setTagDraft('');
  }, [activeScope]);

  const activeTerms = activeScope === 'project' ? projectTerms : globalTerms;
  const focusedTerm = activeTerms.find(term => term.original === focusedOriginal) || null;

  useEffect(() => {
    if (!isCreating && focusedTerm) setEditor(toEditor(focusedTerm));
  }, [focusedTerm, isCreating]);

  const availableTags = useMemo(
    () =>
      Array.from(new Set(activeTerms.flatMap(term => term.tags || []))).sort((a, b) =>
        a.localeCompare(b, 'zh-CN', { sensitivity: 'base' })
      ),
    [activeTerms]
  );

  const filteredTerms = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = activeTerms.filter(term => {
      const tags = term.tags || [];
      return (
        (!query ||
          term.original.toLowerCase().includes(query) ||
          (term.translation || '').toLowerCase().includes(query) ||
          (term.note || '').toLowerCase().includes(query) ||
          tags.some(tag => tag.toLowerCase().includes(query))) &&
        (statusFilter === 'all' || (term.status || 'active') === statusFilter) &&
        (strategyFilter === 'all' || term.strategy === strategyFilter) &&
        (tagFilter === 'all' || tags.some(tag => tag.toLowerCase() === tagFilter.toLowerCase()))
      );
    });
    items.sort((left, right) => {
      if (sortKey === 'original')
        return left.original.localeCompare(right.original, 'zh-CN', { sensitivity: 'base' });
      if (sortKey === 'translation')
        return (left.translation || '').localeCompare(right.translation || '', 'zh-CN', { sensitivity: 'base' });
      return new Date(right.updated_at || 0).getTime() - new Date(left.updated_at || 0).getTime();
    });
    return items;
  }, [activeTerms, search, statusFilter, strategyFilter, tagFilter, sortKey]);

  const groupedTerms = useMemo(() => {
    const groups = new Map<string, GlossaryTerm[]>();
    filteredTerms.forEach(term => {
      const groupTags =
        tagFilter !== 'all' ? [tagFilter] : term.tags && term.tags.length > 0 ? term.tags : ['未分类'];
      groupTags.forEach(tag => {
        const current = groups.get(tag) || [];
        current.push(term);
        groups.set(tag, current);
      });
    });
    return Array.from(groups.entries())
      .map(([tag, terms]) => ({ tag, terms }))
      .sort((left, right) => {
        if (left.tag === '未分类') return 1;
        if (right.tag === '未分类') return -1;
        if (right.terms.length !== left.terms.length) return right.terms.length - left.terms.length;
        return left.tag.localeCompare(right.tag, 'zh-CN', { sensitivity: 'base' });
      });
  }, [filteredTerms, tagFilter]);

  const filteredRecommendations = useMemo(() => {
    const query = search.trim().toLowerCase();
    return recommendations.filter(
      term =>
        !query ||
        term.original.toLowerCase().includes(query) ||
        (term.translation || '').toLowerCase().includes(query) ||
        (term.recommended_reason || '').toLowerCase().includes(query)
    );
  }, [recommendations, search]);

  function focusTerm(term: GlossaryTerm) {
    setIsCreating(false);
    setFocusedOriginal(term.original);
    setEditor(toEditor(term));
  }

  function resetEditor() {
    setIsCreating(false);
    setFocusedOriginal(null);
    setEditor(emptyEditor);
  }

  function toggleSelected(original: string) {
    setSelectedOriginals(current =>
      current.includes(original) ? current.filter(item => item !== original) : [...current, original]
    );
  }

  function startCreate() {
    setIsCreating(true);
    setFocusedOriginal(null);
    setEditor(emptyEditor);
    setTagDraft('');
  }

  function toggleAllVisible(terms: GlossaryTerm[]) {
    const visibleOriginals = terms.map(term => term.original);
    const allSelected =
      visibleOriginals.length > 0 && visibleOriginals.every(original => selectedOriginals.includes(original));
    if (allSelected) {
      setSelectedOriginals(current => current.filter(original => !visibleOriginals.includes(original)));
      return;
    }
    setSelectedOriginals(current => Array.from(new Set([...current, ...visibleOriginals])));
  }

  function addTagFromDraft() {
    const nextTags = normalizeTags(tagDraft);
    if (!nextTags.length) {
      return;
    }
    setEditor(current => ({ ...current, tags: normalizeTags([...current.tags, ...nextTags]) }));
    setTagDraft('');
  }

  function removeEditorTag(tag: string) {
    setEditor(current => ({
      ...current,
      tags: current.tags.filter(item => item.toLowerCase() !== tag.toLowerCase()),
    }));
  }

  function currentTermPayload(): AddTermRequest {
    return {
      original: editor.original.trim(),
      translation: editor.translation.trim() || null,
      strategy: editor.strategy,
      note: editor.note.trim() || null,
      tags: editor.tags,
      status: editor.status,
    };
  }

  async function saveEditor() {
    if (activeScope === 'recommendations') {
      return;
    }

    const payload = currentTermPayload();
    if (!payload.original) {
      toast.warning('原文术语不能为空');
      return;
    }

    setIsSaving(true);
    try {
      if (activeScope === 'project') {
        if (!projectId) {
          toast.error('缺少项目上下文，无法保存项目术语');
          return;
        }
        if (isCreating) {
          await glossaryApi.addProjectTerm(projectId, payload);
        } else if (focusedOriginal) {
          await glossaryApi.updateProjectTerm(projectId, focusedOriginal, payload);
        }
      } else {
        if (isCreating) {
          await glossaryApi.addGlobalTerm(payload);
        } else if (focusedOriginal) {
          await glossaryApi.updateGlobalTerm(focusedOriginal, payload);
        }
      }

      await loadData();
      setIsCreating(false);
      setFocusedOriginal(payload.original);
      toast.success(isCreating ? '术语已创建' : '术语已更新');
    } catch (error) {
      console.error('Failed to save glossary term:', error);
      toast.error('保存术语失败');
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteTerm(original: string) {
    try {
      if (activeScope === 'project') {
        if (!projectId) {
          toast.error('缺少项目上下文，无法删除项目术语');
          return;
        }
        await glossaryApi.deleteProjectTerm(projectId, original);
      } else {
        await glossaryApi.deleteGlobalTerm(original);
      }

      await loadData();
      setSelectedOriginals(current => current.filter(item => item !== original));
      if (focusedOriginal === original) {
        resetEditor();
      }
      toast.success('术语已删除');
    } catch (error) {
      console.error('Failed to delete glossary term:', error);
      toast.error('删除术语失败');
    }
  }

  async function runBatch(action: BatchGlossaryRequest['action'], overrides: Partial<BatchGlossaryRequest> = {}) {
    if (activeScope === 'recommendations') {
      return;
    }
    if (!selectedOriginals.length) {
      toast.warning('请先选择至少一条术语');
      return;
    }

    const request: BatchGlossaryRequest = {
      originals: selectedOriginals,
      action,
      ...overrides,
    };

    try {
      if (activeScope === 'project') {
        if (!projectId) {
          toast.error('缺少项目上下文，无法执行批量操作');
          return;
        }
        await glossaryApi.batchUpdateProjectGlossary(projectId, request);
      } else {
        await glossaryApi.batchUpdateGlobalGlossary(request);
      }

      await loadData();
      setSelectedOriginals([]);
      if (action === 'delete') {
        resetEditor();
      }
      toast.success('批量操作已完成');
    } catch (error) {
      console.error('Failed to run glossary batch action:', error);
      toast.error('批量操作失败');
    }
  }

  async function promoteRecommendation(term: GlossaryRecommendation) {
    if (!projectId) {
      return;
    }
    try {
      await glossaryApi.promoteProjectTerm(projectId, term.original);
      await loadData();
      toast.success('术语已提升到全局');
    } catch (error) {
      console.error('Failed to promote project term:', error);
      toast.error('提升术语失败');
    }
  }

  const projectLabel = projectTitle || projectId || '当前项目';

  function renderListPanel() {
    if (activeScope === 'recommendations') {
      return (
        <RecommendationsList
          projectId={projectId}
          isLoading={isLoading}
          filteredRecommendations={filteredRecommendations}
          onPromote={promoteRecommendation}
        />
      );
    }

    return (
      <div className="space-y-4">
        <div className="grid gap-3 rounded-2xl border border-border bg-white p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_160px_160px_180px_160px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={event => setSearch(event.target.value)}
              placeholder="搜索术语、译法、词义说明、标签"
              className="pl-10"
            />
          </div>
          <Select
            value={statusFilter}
            onValueChange={(value: string) => setStatusFilter(value as 'all' | 'active' | 'disabled')}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">仅 active</SelectItem>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="disabled">仅 disabled</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={strategyFilter}
            onValueChange={(value: string) => setStrategyFilter(value as 'all' | TranslationStrategy)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部策略</SelectItem>
              <SelectItem value="translate">翻译</SelectItem>
              <SelectItem value="first_annotate">首次标注</SelectItem>
              <SelectItem value="preserve">保留原文</SelectItem>
              <SelectItem value="preserve_annotate">保留原文+首次注释</SelectItem>
            </SelectContent>
          </Select>
          <Select value={tagFilter} onValueChange={(value: string) => setTagFilter(value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部标签</SelectItem>
              {availableTags.map(tag => (
                <SelectItem key={tag} value={tag}>
                  {tag}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={sortKey}
            onValueChange={(value: string) => setSortKey(value as SortKey)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated_at">按更新时间</SelectItem>
              <SelectItem value="original">按原文</SelectItem>
              <SelectItem value="translation">按译法</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{filteredTerms.length} 条可见术语</Badge>
            <Badge variant="outline">{scopeLabel(activeScope)}</Badge>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={listMode === 'table' ? 'default' : 'outline'}
              onClick={() => setListMode('table')}
            >
              表格视图
            </Button>
            <Button
              size="sm"
              variant={listMode === 'grouped' ? 'default' : 'outline'}
              onClick={() => setListMode('grouped')}
            >
              按标签分组
            </Button>
            <Button size="sm" leftIcon={<Plus className="h-4 w-4" />} onClick={startCreate}>
              新建术语
            </Button>
          </div>
        </div>

        <BatchActionsBar
          activeScope={activeScope}
          selectedOriginals={selectedOriginals}
          onClearSelection={() => setSelectedOriginals([])}
          onRunBatch={runBatch}
        />

        {listMode === 'grouped' ? (
          <GroupedTermView
            groupedTerms={groupedTerms}
            selectedOriginals={selectedOriginals}
            focusedOriginal={focusedOriginal}
            isCreating={isCreating}
            activeScope={activeScope}
            onToggleSelected={toggleSelected}
            onToggleAllVisible={toggleAllVisible}
            onFocusTerm={focusTerm}
            onDeleteTerm={deleteTerm}
          />
        ) : (
          <TermTable
            terms={filteredTerms}
            tableKey="primary-table"
            selectedOriginals={selectedOriginals}
            focusedOriginal={focusedOriginal}
            isCreating={isCreating}
            activeScope={activeScope}
            onToggleSelected={toggleSelected}
            onToggleAllVisible={toggleAllVisible}
            onFocusTerm={focusTerm}
            onDeleteTerm={deleteTerm}
          />
        )}
      </div>
    );
  }

  function renderTabsContent() {
    return (
      <div className="flex flex-col gap-6">
        {isLoading ? (
          <div className="rounded-2xl border border-border bg-white p-10 text-center text-muted-foreground">
            正在加载术语数据...
          </div>
        ) : (
          renderListPanel()
        )}
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gray-50 px-6 py-6">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-border bg-white p-6 shadow-sm md:flex-row md:items-start md:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              {onBack ? (
                <Button size="sm" variant="outline" leftIcon={<ArrowLeft className="h-4 w-4" />} onClick={onBack}>
                  返回
                </Button>
              ) : null}
              <Badge variant="secondary">
                <BookOpen className="mr-1 h-3.5 w-3.5" />
                术语中心
              </Badge>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">统一术语管理</h1>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                这里统一管理全局术语、项目术语和推荐提升。长文翻译会优先使用项目术语覆盖全局术语；帖子、Slack
                和工具箱当前只使用全局术语。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">当前视图：{scopeLabel(activeScope)}</Badge>
              {projectId ? <Badge variant="secondary">项目：{projectLabel}</Badge> : null}
            </div>
          </div>
        </div>

        <Tabs
          value={activeScope}
          onValueChange={(value: string) => {
            const nextScope: GlossaryScope =
              value === 'project' || value === 'global' || value === 'recommendations' ? value : 'global';
            setActiveScope(nextScope);
          }}
        >
          <TabsList>
            {projectId ? (
              <TabsTrigger value="project" className="gap-1.5">
                <Languages className="h-4 w-4" />
                项目术语
              </TabsTrigger>
            ) : null}
            <TabsTrigger value="global" className="gap-1.5">
              <Globe2 className="h-4 w-4" />
              全局术语
            </TabsTrigger>
            {projectId ? (
              <TabsTrigger value="recommendations" className="gap-1.5">
                <Star className="h-4 w-4" />
                推荐提升
              </TabsTrigger>
            ) : null}
          </TabsList>
          {projectId ? <TabsContent value="project">{renderTabsContent()}</TabsContent> : null}
          <TabsContent value="global">{renderTabsContent()}</TabsContent>
          {projectId ? <TabsContent value="recommendations">{renderTabsContent()}</TabsContent> : null}
        </Tabs>

        {/* 编辑器模态框 */}
        <Dialog open={isCreating || focusedOriginal !== null} onOpenChange={(open) => {
          if (!open) resetEditor();
        }}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{isCreating ? '新建术语' : '编辑术语'}</DialogTitle>
            </DialogHeader>
            <TermEditor
              activeScope={activeScope}
              isCreating={isCreating}
              focusedTerm={focusedTerm}
              editor={editor}
              isSaving={isSaving}
              tagDraft={tagDraft}
              onEditorChange={setEditor}
              onTagDraftChange={setTagDraft}
              onAddTagFromDraft={addTagFromDraft}
              onRemoveEditorTag={removeEditorTag}
              onSave={() => void saveEditor()}
              onDelete={(original) => void deleteTerm(original)}
              onReset={resetEditor}
            />
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
