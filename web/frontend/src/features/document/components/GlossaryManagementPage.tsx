import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, BookOpen, Globe2, Languages, Plus, Search, Star, Trash2 } from 'lucide-react';
import { Button, Input, TabsWithPanel, useToast } from '../../../components/ui';
import { glossaryApi } from '../../confirmation/api/glossaryApi';
import type {
  GlossaryRecommendation,
  GlossaryTerm,
  TranslationStrategy,
} from '../../confirmation/types';

interface GlossaryManagementPageProps {
  projectId: string;
  projectTitle: string;
  onBack: () => void;
}

type GlossaryScope = 'project' | 'global';

interface EditingTerm {
  original: string;
  translation: string;
  strategy: TranslationStrategy;
  note: string;
  status: 'active' | 'disabled';
}

const strategyLabels: Record<TranslationStrategy, string> = {
  preserve: '保留原文',
  first_annotate: '首现括注',
  translate: '翻译',
};

const scopeTabs = [
  { id: 'project', label: '项目术语', icon: <Languages className="h-4 w-4" /> },
  { id: 'global', label: '全局术语', icon: <Globe2 className="h-4 w-4" /> },
];

const emptyEditor: EditingTerm = {
  original: '',
  translation: '',
  strategy: 'translate',
  note: '',
  status: 'active',
};

export function GlossaryManagementPage({
  projectId,
  projectTitle,
  onBack,
}: GlossaryManagementPageProps) {
  const { showToast } = useToast();
  const [activeScope, setActiveScope] = useState<GlossaryScope>('project');
  const [projectTerms, setProjectTerms] = useState<GlossaryTerm[]>([]);
  const [globalTerms, setGlobalTerms] = useState<GlossaryTerm[]>([]);
  const [recommendations, setRecommendations] = useState<GlossaryRecommendation[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editingTerm, setEditingTerm] = useState<GlossaryTerm | null>(null);
  const [editor, setEditor] = useState<EditingTerm>(emptyEditor);

  const loadAll = useCallback(async () => {
    setIsLoading(true);
    try {
      const [projectGlossary, globalGlossary, recommendationData] = await Promise.all([
        glossaryApi.getProjectGlossary(projectId),
        glossaryApi.getGlobalGlossary(),
        glossaryApi.getProjectRecommendations(projectId),
      ]);
      setProjectTerms(projectGlossary.terms);
      setGlobalTerms(globalGlossary.terms);
      setRecommendations(recommendationData.recommendations);
    } catch (error) {
      console.error('Failed to load glossary data:', error);
      showToast('加载术语库失败', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [projectId, showToast]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const resetEditor = useCallback(() => {
    setEditingTerm(null);
    setEditor(emptyEditor);
  }, []);

  const activeTerms = activeScope === 'project' ? projectTerms : globalTerms;

  const filteredTerms = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return activeTerms;
    }

    return activeTerms.filter(term => {
      return (
        term.original.toLowerCase().includes(query) ||
        (term.translation || '').toLowerCase().includes(query) ||
        (term.note || '').toLowerCase().includes(query)
      );
    });
  }, [activeTerms, search]);

  const beginAdd = () => {
    setEditingTerm(null);
    setEditor(emptyEditor);
  };

  const beginEdit = (term: GlossaryTerm) => {
    setEditingTerm(term);
    setEditor({
      original: term.original,
      translation: term.translation || '',
      strategy: term.strategy,
      note: term.note || '',
      status: (term.status as 'active' | 'disabled') || 'active',
    });
  };

  const handleSave = async () => {
    if (!editor.original.trim()) {
      showToast('术语原文不能为空', 'warning');
      return;
    }

    setIsSaving(true);
    try {
      if (activeScope === 'project') {
        if (editingTerm) {
          await glossaryApi.updateProjectTerm(projectId, editingTerm.original, editor);
        } else {
          await glossaryApi.addProjectTerm(projectId, editor);
        }
      } else {
        if (editingTerm) {
          await glossaryApi.updateGlobalTerm(editingTerm.original, editor);
        } else {
          await glossaryApi.addGlobalTerm(editor);
        }
      }
      await loadAll();
      resetEditor();
      showToast('术语已保存', 'success');
    } catch (error) {
      console.error('Failed to save glossary term:', error);
      showToast('保存术语失败', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (term: GlossaryTerm) => {
    const confirmed = window.confirm(`确定要删除术语 “${term.original}” 吗？`);
    if (!confirmed) {
      return;
    }

    try {
      if (activeScope === 'project') {
        await glossaryApi.deleteProjectTerm(projectId, term.original);
      } else {
        await glossaryApi.deleteGlobalTerm(term.original);
      }
      await loadAll();
      if (editingTerm?.original === term.original) {
        resetEditor();
      }
      showToast('术语已删除', 'success');
    } catch (error) {
      console.error('Failed to delete glossary term:', error);
      showToast('删除术语失败', 'error');
    }
  };

  const handlePromote = async (term: GlossaryRecommendation | GlossaryTerm) => {
    try {
      await glossaryApi.promoteProjectTerm(projectId, term.original);
      await loadAll();
      showToast('已提升到全局术语库', 'success');
    } catch (error) {
      console.error('Failed to promote term:', error);
      showToast('提升到全局失败', 'error');
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-primary-600">
            <BookOpen className="h-4 w-4" />
            术语管理
          </div>
          <h1 className="text-2xl font-bold text-text-primary">{projectTitle}</h1>
          <p className="mt-2 text-sm text-text-muted">
            管理项目术语、全局术语以及推荐提升列表。项目术语优先于全局术语，适合先沉淀当前文章里的术语决策。
          </p>
        </div>
        <Button variant="secondary" onClick={onBack} leftIcon={<ArrowLeft className="h-4 w-4" />}>
          返回文章
        </Button>
      </div>

      <TabsWithPanel
        tabs={scopeTabs}
        activeTab={activeScope}
        onChange={tabId => {
          setActiveScope(tabId as GlossaryScope);
          resetEditor();
        }}
        variant="segmented"
        size="sm"
        renderPanel={() => (
          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              {activeScope === 'project' && recommendations.length > 0 && (
                <section className="rounded-2xl border border-border-subtle bg-bg-secondary p-5">
                  <div className="mb-3 flex items-center gap-2 text-sm font-medium text-text-primary">
                    <Star className="h-4 w-4 text-warning" />
                    待提升区
                  </div>
                  <div className="space-y-3">
                    {recommendations.map(term => (
                      <div
                        key={`recommend-${term.original}`}
                        className="rounded-xl border border-border-subtle bg-bg-primary p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div className="font-semibold text-text-primary">
                              {term.original} → {term.translation || '保留原文'}
                            </div>
                            <div className="mt-1 text-sm text-text-muted">
                              {term.recommended_reason} · 出现 {term.usage_count} 次
                            </div>
                            {term.note && (
                              <div className="mt-1 text-sm text-text-muted">{term.note}</div>
                            )}
                          </div>
                          <Button variant="primary" size="sm" onClick={() => void handlePromote(term)}>
                            提升到全局
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <section className="rounded-2xl border border-border-subtle bg-bg-secondary p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="relative min-w-[260px] flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                    <Input
                      value={search}
                      onChange={event => setSearch(event.target.value)}
                      placeholder={activeScope === 'project' ? '搜索项目术语' : '搜索全局术语'}
                      className="pl-10"
                    />
                  </div>
                  <Button variant="secondary" onClick={beginAdd} leftIcon={<Plus className="h-4 w-4" />}>
                    新增术语
                  </Button>
                </div>

                <div className="mb-3 text-sm text-text-muted">
                  {activeScope === 'project' ? '项目术语' : '全局术语'}共 {activeTerms.length} 条
                  {filteredTerms.length !== activeTerms.length ? `，当前显示 ${filteredTerms.length} 条` : ''}
                </div>

                <div className="space-y-3">
                  {isLoading ? (
                    <div className="rounded-xl border border-border-subtle bg-bg-primary p-6 text-center text-text-muted">
                      正在加载术语库...
                    </div>
                  ) : filteredTerms.length === 0 ? (
                    <div className="rounded-xl border border-border-subtle bg-bg-primary p-6 text-center text-text-muted">
                      当前没有匹配的术语。
                    </div>
                  ) : (
                    filteredTerms.map(term => (
                      <div
                        key={`${activeScope}-${term.original}`}
                        className={`rounded-xl border p-4 transition-colors ${
                          editingTerm?.original === term.original
                            ? 'border-primary-500 bg-primary-500/5'
                            : 'border-border-subtle bg-bg-primary hover:border-primary-400/50'
                        }`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold text-text-primary">{term.original}</span>
                              <span className="rounded-full bg-primary-500/10 px-2 py-0.5 text-xs text-primary-600">
                                {strategyLabels[term.strategy]}
                              </span>
                              {term.status === 'disabled' && (
                                <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-600">
                                  已禁用
                                </span>
                              )}
                              {term.source && (
                                <span className="rounded-full bg-bg-tertiary px-2 py-0.5 text-xs text-text-muted">
                                  {term.source}
                                </span>
                              )}
                            </div>
                            <div className="mt-1 text-sm text-text-secondary">
                              {term.translation || '保留原文'}
                            </div>
                            {term.note && (
                              <div className="mt-1 text-sm text-text-muted">{term.note}</div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            {activeScope === 'project' && term.translation && (
                              <Button size="sm" variant="secondary" onClick={() => void handlePromote(term)}>
                                提升
                              </Button>
                            )}
                            <Button size="sm" variant="secondary" onClick={() => beginEdit(term)}>
                              编辑
                            </Button>
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => void handleDelete(term)}
                              leftIcon={<Trash2 className="h-3.5 w-3.5" />}
                            >
                              删除
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </div>

            <section className="rounded-2xl border border-border-subtle bg-bg-secondary p-5">
              <div className="mb-4 text-lg font-semibold text-text-primary">
                {editingTerm ? '编辑术语' : '新增术语'}
              </div>

              <div className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-text-primary">原文术语</label>
                  <Input
                    value={editor.original}
                    onChange={event => setEditor(current => ({ ...current, original: event.target.value }))}
                    disabled={!!editingTerm}
                    placeholder="例如：chiplet"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-text-primary">译法</label>
                  <Input
                    value={editor.translation}
                    onChange={event => setEditor(current => ({ ...current, translation: event.target.value }))}
                    placeholder="例如：芯粒"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-text-primary">翻译策略</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(Object.keys(strategyLabels) as TranslationStrategy[]).map(strategy => (
                      <button
                        key={strategy}
                        type="button"
                        onClick={() => setEditor(current => ({ ...current, strategy }))}
                        className={`rounded-lg border px-3 py-2 text-sm ${
                          editor.strategy === strategy
                            ? 'border-primary-500 bg-primary-500/10 text-primary-600'
                            : 'border-border-subtle text-text-secondary'
                        }`}
                      >
                        {strategyLabels[strategy]}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-text-primary">状态</label>
                  <select
                    value={editor.status}
                    onChange={event =>
                      setEditor(current => ({
                        ...current,
                        status: event.target.value as 'active' | 'disabled',
                      }))
                    }
                    className="w-full rounded-lg border border-border-subtle bg-bg-primary px-3 py-2 text-sm text-text-primary"
                  >
                    <option value="active">启用</option>
                    <option value="disabled">禁用</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-text-primary">备注</label>
                  <textarea
                    value={editor.note}
                    onChange={event => setEditor(current => ({ ...current, note: event.target.value }))}
                    rows={5}
                    placeholder="补充适用语境、是否首现括注、为何要保留英文等"
                    className="w-full rounded-lg border border-border-subtle bg-bg-primary px-3 py-2 text-sm text-text-primary outline-none focus:border-primary-500"
                  />
                </div>

                <div className="flex gap-3">
                  <Button variant="secondary" className="flex-1" onClick={resetEditor}>
                    重置
                  </Button>
                  <Button
                    variant="primary"
                    className="flex-1"
                    onClick={() => void handleSave()}
                    isLoading={isSaving}
                  >
                    保存
                  </Button>
                </div>
              </div>
            </section>
          </div>
        )}
      />
    </div>
  );
}
