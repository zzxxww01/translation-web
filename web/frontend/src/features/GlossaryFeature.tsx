import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, Globe2, Languages, Plus, Search, Star, Tag, Trash2 } from 'lucide-react';
import { Badge, Button, Input, TabsWithPanel, Textarea, useToast } from '../components/ui';
import { glossaryApi, type AddTermRequest, type BatchGlossaryRequest } from './confirmation/api/glossaryApi';
import type { GlossaryRecommendation, GlossaryTerm, TranslationStrategy } from './confirmation/types';

type GlossaryScope = 'project' | 'global' | 'recommendations';
type SortKey = 'updated_at' | 'original' | 'translation';
type ListMode = 'table' | 'grouped';

interface EditingTerm {
  original: string;
  translation: string;
  strategy: TranslationStrategy;
  note: string;
  tags: string[];
  status: 'active' | 'disabled';
}

interface GlossaryCenterProps {
  projectId?: string | null;
  projectTitle?: string | null;
  defaultScope?: GlossaryScope;
  onBack?: () => void;
}

const strategyLabels: Record<TranslationStrategy, string> = {
  preserve: '保留原文',
  first_annotate: '首次标注',
  translate: '翻译',
};

const emptyEditor: EditingTerm = {
  original: '',
  translation: '',
  strategy: 'translate',
  note: '',
  tags: [],
  status: 'active',
};

function normalizeTags(raw: string[] | string): string[] {
  const items = Array.isArray(raw) ? raw : raw.split(',');
  const seen = new Set<string>();
  const result: string[] = [];
  items.map(item => item.trim()).filter(Boolean).forEach(item => {
    const key = item.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    result.push(item);
  });
  return result;
}

function toEditor(term: GlossaryTerm): EditingTerm {
  return {
    original: term.original,
    translation: term.translation || '',
    strategy: term.strategy,
    note: term.note || '',
    tags: [...(term.tags || [])],
    status: (term.status as 'active' | 'disabled') || 'active',
  };
}

function scopeLabel(scope: GlossaryScope): string {
  if (scope === 'project') return '????';
  if (scope === 'recommendations') return '????';
  return '????';
}

export function GlossaryCenter({ projectId, projectTitle, defaultScope = 'global', onBack }: GlossaryCenterProps) {
  const { showToast } = useToast();
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
  const [batchTagInput, setBatchTagInput] = useState('');
  const [batchStrategy, setBatchStrategy] = useState<TranslationStrategy>('translate');

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
        const [projectGlossary, globalGlossary, recommendationData] = results as [{ terms: GlossaryTerm[] }, { terms: GlossaryTerm[] }, { recommendations: GlossaryRecommendation[] }];
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
      showToast('加载术语中心失败', 'error');
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

  const tabs = useMemo(() => {
    const items: Array<{ id: string; label: string; icon: ReactNode }> = [];
    if (projectId) items.push({ id: 'project', label: '项目术语', icon: <Languages className="h-4 w-4" /> });
    items.push({ id: 'global', label: '全局术语', icon: <Globe2 className="h-4 w-4" /> });
    if (projectId) items.push({ id: 'recommendations', label: '推荐提升', icon: <Star className="h-4 w-4" /> });
    return items;
  }, [projectId]);

  const activeTerms = activeScope === 'project' ? projectTerms : globalTerms;
  const focusedTerm = activeTerms.find(term => term.original === focusedOriginal) || null;

  useEffect(() => {
    if (!isCreating && focusedTerm) setEditor(toEditor(focusedTerm));
  }, [focusedTerm, isCreating]);

  const availableTags = useMemo(() => Array.from(new Set(activeTerms.flatMap(term => term.tags || []))).sort((a, b) => a.localeCompare(b, 'zh-CN', { sensitivity: 'base' })), [activeTerms]);

  const filteredTerms = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = activeTerms.filter(term => {
      const tags = term.tags || [];
      return ((!query || term.original.toLowerCase().includes(query) || (term.translation || '').toLowerCase().includes(query) || (term.note || '').toLowerCase().includes(query) || tags.some(tag => tag.toLowerCase().includes(query))) && (statusFilter === 'all' || (term.status || 'active') === statusFilter) && (strategyFilter === 'all' || term.strategy === strategyFilter) && (tagFilter === 'all' || tags.some(tag => tag.toLowerCase() === tagFilter.toLowerCase())));
    });
    items.sort((left, right) => {
      if (sortKey === 'original') return left.original.localeCompare(right.original, 'zh-CN', { sensitivity: 'base' });
      if (sortKey === 'translation') return (left.translation || '').localeCompare(right.translation || '', 'zh-CN', { sensitivity: 'base' });
      return new Date(right.updated_at || 0).getTime() - new Date(left.updated_at || 0).getTime();
    });
    return items;
  }, [activeTerms, search, statusFilter, strategyFilter, tagFilter, sortKey]);

  const groupedTerms = useMemo(() => {
    const groups = new Map<string, GlossaryTerm[]>();
    filteredTerms.forEach(term => {
      const groupTags = tagFilter !== 'all' ? [tagFilter] : term.tags && term.tags.length > 0 ? term.tags : ['未分类'];
      groupTags.forEach(tag => {
        const current = groups.get(tag) || [];
        current.push(term);
        groups.set(tag, current);
      });
    });
    return Array.from(groups.entries()).map(([tag, terms]) => ({ tag, terms })).sort((left, right) => {
      if (left.tag === '未分类') return 1;
      if (right.tag === '未分类') return -1;
      if (right.terms.length !== left.terms.length) return right.terms.length - left.terms.length;
      return left.tag.localeCompare(right.tag, 'zh-CN', { sensitivity: 'base' });
    });
  }, [filteredTerms, tagFilter]);

  const filteredRecommendations = useMemo(() => {
    const query = search.trim().toLowerCase();
    return recommendations.filter(term => !query || term.original.toLowerCase().includes(query) || (term.translation || '').toLowerCase().includes(query) || (term.recommended_reason || '').toLowerCase().includes(query));
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
    setSelectedOriginals(current => current.includes(original) ? current.filter(item => item !== original) : [...current, original]);
  }

  function startCreate() {
    setIsCreating(true);
    setFocusedOriginal(null);
    setEditor(emptyEditor);
    setTagDraft('');
  }

  function toggleAllVisible(terms: GlossaryTerm[]) {
    const visibleOriginals = terms.map(term => term.original);
    const allSelected = visibleOriginals.length > 0 && visibleOriginals.every(original => selectedOriginals.includes(original));
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
      showToast('原文术语不能为空', 'warning');
      return;
    }

    setIsSaving(true);
    try {
      if (activeScope === 'project') {
        if (!projectId) {
          showToast('缺少项目上下文，无法保存项目术语', 'error');
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
      showToast(isCreating ? '术语已创建' : '术语已更新', 'success');
    } catch (error) {
      console.error('Failed to save glossary term:', error);
      showToast('保存术语失败', 'error');
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteTerm(original: string) {
    const confirmed = window.confirm(
      activeScope === 'project'
        ? '删除项目术语后，只会移除项目覆盖，不会影响全局术语。确认继续？'
        : '删除全局术语后，所有依赖全局术语的功能都会受影响。确认继续？'
    );
    if (!confirmed) {
      return;
    }

    try {
      if (activeScope === 'project') {
        if (!projectId) {
          showToast('缺少项目上下文，无法删除项目术语', 'error');
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
      showToast('术语已删除', 'success');
    } catch (error) {
      console.error('Failed to delete glossary term:', error);
      showToast('删除术语失败', 'error');
    }
  }

  async function runBatch(action: BatchGlossaryRequest['action'], overrides: Partial<BatchGlossaryRequest> = {}) {
    if (activeScope === 'recommendations') {
      return;
    }
    if (!selectedOriginals.length) {
      showToast('请先选择至少一条术语', 'warning');
      return;
    }
    if (action === 'delete') {
      const confirmed = window.confirm(
        activeScope === 'project'
          ? '批量删除项目术语后，只会移除项目覆盖。确认继续？'
          : '批量删除全局术语后，所有依赖全局术语的功能都会受影响。确认继续？'
      );
      if (!confirmed) {
        return;
      }
    }

    const request: BatchGlossaryRequest = {
      originals: selectedOriginals,
      action,
      ...overrides,
    };

    try {
      if (activeScope === 'project') {
        if (!projectId) {
          showToast('缺少项目上下文，无法执行批量操作', 'error');
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
      showToast('批量操作已完成', 'success');
    } catch (error) {
      console.error('Failed to run glossary batch action:', error);
      showToast('批量操作失败', 'error');
    }
  }

  async function promoteRecommendation(term: GlossaryRecommendation) {
    if (!projectId) {
      return;
    }
    try {
      await glossaryApi.promoteProjectTerm(projectId, term.original);
      await loadData();
      showToast('术语已提升到全局', 'success');
    } catch (error) {
      console.error('Failed to promote project term:', error);
      showToast('提升术语失败', 'error');
    }
  }

  function renderTermRows(terms: GlossaryTerm[]) {
    return terms.map(term => {
      const isSelected = selectedOriginals.includes(term.original);
      const isFocused = focusedOriginal === term.original && !isCreating;
      return (
        <tr key={term.original} className={isFocused ? 'bg-primary-50/70' : 'hover:bg-bg-tertiary/70'}>
          <td className="px-3 py-3 align-top">
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => toggleSelected(term.original)}
              aria-label={`选择 ${term.original}`}
            />
          </td>
          <td className="px-3 py-3 align-top">
            <button
              type="button"
              className="text-left font-medium text-text-primary hover:text-primary"
              onClick={() => focusTerm(term)}
            >
              {term.original}
            </button>
          </td>
          <td className="px-3 py-3 align-top text-text-secondary">{term.translation || '-'}</td>
          <td className="px-3 py-3 align-top">
            <Badge variant="outline">{strategyLabels[term.strategy]}</Badge>
          </td>
          <td className="px-3 py-3 align-top">
            <div className="flex flex-wrap gap-1">
              {(term.tags || []).length ? (
                (term.tags || []).map(tag => (
                  <Badge key={`${term.original}-${tag}`} variant="secondary">
                    {tag}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-text-muted">未分类</span>
              )}
            </div>
          </td>
          <td className="px-3 py-3 align-top">
            <Badge variant={(term.status || 'active') === 'disabled' ? 'secondary' : 'default'}>
              {term.status || 'active'}
            </Badge>
          </td>
          <td className="px-3 py-3 align-top text-sm text-text-muted">
            {term.updated_at ? new Date(term.updated_at).toLocaleString() : '-'}
          </td>
          <td className="px-3 py-3 align-top">
            <div className="flex items-center gap-2">
              <Button size="sm" variant="secondary" onClick={() => focusTerm(term)}>
                编辑
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="text-error hover:text-error"
                onClick={() => void deleteTerm(term.original)}
              >
                删除
              </Button>
            </div>
          </td>
        </tr>
      );
    });
  }

  function renderTermTable(terms: GlossaryTerm[], tableKey: string) {
    if (!terms.length) {
      return (
        <div className="rounded-2xl border border-dashed border-border p-10 text-center text-text-muted">
          当前筛选条件下没有术语。
        </div>
      );
    }

    const visibleOriginals = terms.map(term => term.original);
    const allSelected = visibleOriginals.length > 0 && visibleOriginals.every(original => selectedOriginals.includes(original));

    return (
      <div key={tableKey} className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-bg-secondary/80 text-left text-text-secondary">
              <tr>
                <th className="px-3 py-3">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={() => toggleAllVisible(terms)}
                    aria-label="选择当前列表全部术语"
                  />
                </th>
                <th className="px-3 py-3">原文</th>
                <th className="px-3 py-3">译法</th>
                <th className="px-3 py-3">策略</th>
                <th className="px-3 py-3">标签</th>
                <th className="px-3 py-3">状态</th>
                <th className="px-3 py-3">更新时间</th>
                <th className="px-3 py-3">操作</th>
              </tr>
            </thead>
            <tbody>{renderTermRows(terms)}</tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderGroupedView() {
    if (!groupedTerms.length) {
      return (
        <div className="rounded-2xl border border-dashed border-border p-10 text-center text-text-muted">
          当前筛选条件下没有术语。
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {groupedTerms.map(group => (
          <section key={group.tag} className="space-y-3">
            <div className="flex items-center gap-3">
              <Badge variant="secondary" className="px-3 py-1 text-sm">
                <Tag className="mr-1 h-3.5 w-3.5" />
                {group.tag}
              </Badge>
              <span className="text-sm text-text-muted">{group.terms.length} 条</span>
            </div>
            {renderTermTable(group.terms, `group-${group.tag}`)}
          </section>
        ))}
      </div>
    );
  }

  function renderRecommendations() {
    if (!projectId) {
      return null;
    }
    if (isLoading) {
      return (
        <div className="rounded-2xl border border-border bg-white p-10 text-center text-text-muted">
          正在加载推荐提升...
        </div>
      );
    }
    if (!filteredRecommendations.length) {
      return (
        <div className="rounded-2xl border border-dashed border-border p-10 text-center text-text-muted">
          当前没有可提升的项目术语推荐。
        </div>
      );
    }
    return (
      <div className="space-y-4">
        {filteredRecommendations.map(term => (
          <div key={term.original} className="rounded-2xl border border-border bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-lg font-semibold text-text-primary">{term.original}</h3>
                  <Badge variant="outline">{strategyLabels[term.strategy]}</Badge>
                  <Badge variant="secondary">使用 {term.usage_count} 次</Badge>
                </div>
                <div className="text-text-secondary">译法：{term.translation || '保留原文'}</div>
                {term.note ? (
                  <div className="text-sm text-text-secondary">词义说明：{term.note}</div>
                ) : null}
                <p className="text-sm text-text-secondary">{term.recommended_reason}</p>
                <div className="flex flex-wrap gap-2">
                  {(term.tags || []).map(tag => (
                    <Badge key={`${term.original}-${tag}`} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
                <div className="text-sm text-text-muted">
                  涉及章节：
                  {term.section_titles.length ? term.section_titles.map(item => item.title).join(' / ') : '未记录章节'}
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void promoteRecommendation(term)}>
                  提升到全局
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  function renderBatchBar() {
    if (activeScope === 'recommendations' || !selectedOriginals.length) {
      return null;
    }
    return (
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm text-text-secondary">已选择 {selectedOriginals.length} 条术语</div>
          <Button size="sm" variant="secondary" onClick={() => setSelectedOriginals([])}>
            清空选择
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="secondary" onClick={() => void runBatch('set_status', { status: 'active' })}>
            批量启用
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void runBatch('set_status', { status: 'disabled' })}>
            批量停用
          </Button>
          <select
            value={batchStrategy}
            onChange={event => setBatchStrategy(event.target.value as TranslationStrategy)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
          >
            <option value="translate">翻译</option>
            <option value="first_annotate">首次标注</option>
            <option value="preserve">保留原文</option>
          </select>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => void runBatch('set_strategy', { strategy: batchStrategy })}
          >
            批量改策略
          </Button>
          <Input
            value={batchTagInput}
            onChange={event => setBatchTagInput(event.target.value)}
            placeholder="标签，逗号分隔"
            className="min-w-[220px]"
          />
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              const tags = normalizeTags(batchTagInput);
              if (!tags.length) {
                showToast('请输入至少一个标签', 'warning');
                return;
              }
              setBatchTagInput('');
              void runBatch('add_tags', { tags });
            }}
          >
            批量加标签
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              const tags = normalizeTags(batchTagInput);
              if (!tags.length) {
                showToast('请输入至少一个标签', 'warning');
                return;
              }
              setBatchTagInput('');
              void runBatch('replace_tags', { tags });
            }}
          >
            替换标签
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              const tags = normalizeTags(batchTagInput);
              if (!tags.length) {
                showToast('请输入至少一个标签', 'warning');
                return;
              }
              setBatchTagInput('');
              void runBatch('remove_tags', { tags });
            }}
          >
            移除标签
          </Button>
          <Button size="sm" variant="danger" leftIcon={<Trash2 className="h-4 w-4" />} onClick={() => void runBatch('delete')}>
            批量删除
          </Button>
        </div>
      </div>
    );
  }

  function renderEditor() {
    if (activeScope === 'recommendations') {
      return (
        <div className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-text-primary">
            <Star className="h-4 w-4" />
            <h3 className="font-semibold">推荐提升说明</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            这里展示的是项目内高频、适合沉淀为全局标准的术语。提升到全局后，帖子翻译、Slack、工具箱和其他项目都可以复用。
          </p>
        </div>
      );
    }

    if (!isCreating && !focusedTerm) {
      return (
        <div className="rounded-2xl border border-dashed border-border bg-white p-8 text-center text-text-muted">
          从左侧列表选择一条术语，或创建新术语。
        </div>
      );
    }

    return (
      <div className="rounded-2xl border border-border bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-text-primary">{isCreating ? '新建术语' : '编辑术语'}</h3>
            <p className="text-sm text-text-muted">{scopeLabel(activeScope)}</p>
          </div>
          <Button size="sm" variant="secondary" onClick={resetEditor}>
            取消
          </Button>
        </div>

        <div className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-text-secondary">原文术语</label>
            <Input
              value={editor.original}
              disabled={!isCreating}
              onChange={event => setEditor(current => ({ ...current, original: event.target.value }))}
              placeholder="例如 TSMC"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text-secondary">译法</label>
            <Input
              value={editor.translation}
              onChange={event => setEditor(current => ({ ...current, translation: event.target.value }))}
              placeholder="例如 台积电"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-text-secondary">策略</label>
              <select
                value={editor.strategy}
                onChange={event =>
                  setEditor(current => ({ ...current, strategy: event.target.value as TranslationStrategy }))
                }
                className="w-full rounded-xl border border-border bg-white px-3 py-2.5 text-sm"
              >
                <option value="translate">翻译</option>
                <option value="first_annotate">首次标注</option>
                <option value="preserve">保留原文</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-secondary">状态</label>
              <select
                value={editor.status}
                onChange={event =>
                  setEditor(current => ({ ...current, status: event.target.value as 'active' | 'disabled' }))
                }
                className="w-full rounded-xl border border-border bg-white px-3 py-2.5 text-sm"
              >
                <option value="active">active</option>
                <option value="disabled">disabled</option>
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text-secondary">词义说明</label>
            <Textarea
              value={editor.note}
              onChange={event => setEditor(current => ({ ...current, note: event.target.value }))}
              rows={4}
              placeholder="说明这里指的是什么意思，为什么在当前语境下要这样翻"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text-secondary">标签</label>
            <div className="flex gap-2">
              <Input
                value={tagDraft}
                onChange={event => setTagDraft(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    addTagFromDraft();
                  }
                }}
                placeholder="输入标签，逗号分隔"
              />
              <Button size="sm" variant="secondary" onClick={addTagFromDraft}>
                添加标签
              </Button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {editor.tags.length ? (
                editor.tags.map(tag => (
                  <button
                    key={tag}
                    type="button"
                    className="inline-flex items-center gap-1 rounded-full border border-border bg-bg-secondary px-3 py-1 text-sm text-text-secondary"
                    onClick={() => removeEditorTag(tag)}
                  >
                    {tag}
                    <span aria-hidden="true">x</span>
                  </button>
                ))
              ) : (
                <span className="text-sm text-text-muted">尚未添加标签</span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap justify-end gap-2 pt-2">
            {!isCreating && focusedTerm ? (
              <Button size="sm" variant="danger" onClick={() => void deleteTerm(focusedTerm.original)}>
                删除
              </Button>
            ) : null}
            <Button size="sm" variant="secondary" onClick={resetEditor}>
              取消
            </Button>
            <Button size="sm" isLoading={isSaving} onClick={() => void saveEditor()}>
              保存术语
            </Button>
          </div>
        </div>
      </div>
    );
  }

  function renderListPanel() {
    if (activeScope === 'recommendations') {
      return renderRecommendations();
    }

    return (
      <div className="space-y-4">
        <div className="grid gap-3 rounded-2xl border border-border bg-white p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_160px_160px_180px_160px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <Input
              value={search}
              onChange={event => setSearch(event.target.value)}
              placeholder="搜索术语、译法、词义说明、标签"
              className="pl-10"
            />
          </div>
          <select
            value={statusFilter}
            onChange={event => setStatusFilter(event.target.value as 'all' | 'active' | 'disabled')}
            className="rounded-xl border border-border bg-white px-3 py-2.5 text-sm"
          >
            <option value="active">仅 active</option>
            <option value="all">全部状态</option>
            <option value="disabled">仅 disabled</option>
          </select>
          <select
            value={strategyFilter}
            onChange={event => setStrategyFilter(event.target.value as 'all' | TranslationStrategy)}
            className="rounded-xl border border-border bg-white px-3 py-2.5 text-sm"
          >
            <option value="all">全部策略</option>
            <option value="translate">翻译</option>
            <option value="first_annotate">首次标注</option>
            <option value="preserve">保留原文</option>
          </select>
          <select
            value={tagFilter}
            onChange={event => setTagFilter(event.target.value)}
            className="rounded-xl border border-border bg-white px-3 py-2.5 text-sm"
          >
            <option value="all">全部标签</option>
            {availableTags.map(tag => (
              <option key={tag} value={tag}>
                {tag}
              </option>
            ))}
          </select>
          <select
            value={sortKey}
            onChange={event => setSortKey(event.target.value as SortKey)}
            className="rounded-xl border border-border bg-white px-3 py-2.5 text-sm"
          >
            <option value="updated_at">按更新时间</option>
            <option value="original">按原文</option>
            <option value="translation">按译法</option>
          </select>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{filteredTerms.length} 条可见术语</Badge>
            <Badge variant="outline">{scopeLabel(activeScope)}</Badge>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={listMode === 'table' ? 'primary' : 'secondary'}
              onClick={() => setListMode('table')}
            >
              表格视图
            </Button>
            <Button
              size="sm"
              variant={listMode === 'grouped' ? 'primary' : 'secondary'}
              onClick={() => setListMode('grouped')}
            >
              按标签分组
            </Button>
            <Button size="sm" leftIcon={<Plus className="h-4 w-4" />} onClick={startCreate}>
              新建术语
            </Button>
          </div>
        </div>

        {renderBatchBar()}
        {listMode === 'grouped' ? renderGroupedView() : renderTermTable(filteredTerms, 'primary-table')}
      </div>
    );
  }

  const projectLabel = projectTitle || projectId || '当前项目';

  return (
    <div className="min-h-full bg-gradient-to-br from-bg-secondary via-white to-primary-50/20 px-6 py-6">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-border bg-white/90 p-6 shadow-sm backdrop-blur md:flex-row md:items-start md:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              {onBack ? (
                <Button size="sm" variant="secondary" leftIcon={<ArrowLeft className="h-4 w-4" />} onClick={onBack}>
                  返回
                </Button>
              ) : null}
              <Badge variant="secondary">
                <BookOpen className="mr-1 h-3.5 w-3.5" />
                术语中心
              </Badge>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">统一术语管理</h1>
              <p className="mt-2 text-sm leading-6 text-text-secondary">
                这里统一管理全局术语、项目术语和推荐提升。长文翻译会优先使用项目术语覆盖全局术语；帖子、Slack 和工具箱当前只使用全局术语。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">当前视图：{scopeLabel(activeScope)}</Badge>
              {projectId ? <Badge variant="secondary">项目：{projectLabel}</Badge> : null}
            </div>
          </div>
        </div>

        <TabsWithPanel
          tabs={tabs}
          activeTab={activeScope}
          onChange={tabId => {
            const nextScope: GlossaryScope =
              tabId === 'project' || tabId === 'global' || tabId === 'recommendations' ? tabId : 'global';
            setActiveScope(nextScope);
          }}
          variant="segmented"
          renderPanel={() => (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div>
                {isLoading ? (
                  <div className="rounded-2xl border border-border bg-white p-10 text-center text-text-muted">
                    正在加载术语数据...
                  </div>
                ) : (
                  renderListPanel()
                )}
              </div>
              <div>{renderEditor()}</div>
            </div>
          )}
        />
      </div>
    </div>
  );
}

export function GlossaryFeature() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('projectId');
  const projectTitle = searchParams.get('projectTitle');
  const from = searchParams.get('from');
  const scope = searchParams.get('scope');

  const defaultScope: GlossaryScope =
    scope === 'project' || scope === 'recommendations' || scope === 'global' ? scope : 'global';

  return (
    <GlossaryCenter
      projectId={projectId}
      projectTitle={projectTitle}
      defaultScope={defaultScope}
      onBack={() => {
        if (from) {
          navigate(from);
          return;
        }
        navigate(-1);
      }}
    />
  );
}
