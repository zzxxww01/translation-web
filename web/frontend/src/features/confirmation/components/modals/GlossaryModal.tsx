/**
 * 术语库模态框组件
 * 提供术语库查看、搜索、添加、编辑、删除功能
 */

import { useState, useCallback, useEffect } from 'react';
import { Search, Plus, Edit, BookOpen, X, Check } from 'lucide-react';
import { Modal } from '../../../../components/ui/Modal';
import { Button } from '../../../../components/ui';
import { Input } from '../../../../components/ui/Input/Input';
import { glossaryApi } from '../../api/glossaryApi';
import { cn } from '../../../../shared/utils';
import type { GlossaryTerm, TranslationStrategy } from '../../types';

interface GlossaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId?: string;
}

const strategyLabels: Record<TranslationStrategy, string> = {
  preserve: '保留原文',
  first_annotate: '首次注释',
  translate: '翻译',
};

const strategyColors: Record<TranslationStrategy, string> = {
  preserve: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  first_annotate: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  translate: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
};

interface EditingTerm {
  original: string;
  translation: string;
  strategy: TranslationStrategy;
  note: string;
}

export function GlossaryModal({ isOpen, onClose, projectId: _projectId }: GlossaryModalProps) {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [filteredTerms, setFilteredTerms] = useState<GlossaryTerm[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // 添加/编辑术语
  const [isAdding, setIsAdding] = useState(false);
  const [editingTerm, setEditingTerm] = useState<GlossaryTerm | null>(null);
  const [editForm, setEditForm] = useState<EditingTerm>({
    original: '',
    translation: '',
    strategy: 'translate',
    note: '',
  });

  // 加载全局术语表
  const loadGlossary = useCallback(async () => {
    setIsLoading(true);
    try {
      // 使用全局术语库
      const data = await glossaryApi.getGlobalGlossary();
      setTerms(data.terms);
      setFilteredTerms(data.terms);
    } catch (error) {
      console.error('Failed to load glossary:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadGlossary();
    }
  }, [isOpen, loadGlossary]);

  // 搜索过滤
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredTerms(terms);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredTerms(
        terms.filter(
          (term) =>
            term.original.toLowerCase().includes(query) ||
            (term.translation && term.translation.toLowerCase().includes(query)) ||
            (term.note && term.note.toLowerCase().includes(query))
        )
      );
    }
  }, [searchQuery, terms]);

  // 重置表单
  const resetForm = useCallback(() => {
    setEditForm({
      original: '',
      translation: '',
      strategy: 'translate',
      note: '',
    });
    setIsAdding(false);
    setEditingTerm(null);
  }, []);

  // 开始添加术语
  const handleAdd = useCallback(() => {
    resetForm();
    setIsAdding(true);
  }, [resetForm]);

  // 开始编辑术语
  const handleEdit = useCallback(
    (term: GlossaryTerm) => {
      setEditForm({
        original: term.original,
        translation: term.translation || '',
        strategy: term.strategy,
        note: term.note || '',
      });
      setEditingTerm(term);
      setIsAdding(false);
    },
    []
  );

  // 保存术语
  const handleSave = useCallback(async () => {
    if (!editForm.original.trim()) {
      return;
    }

    setIsSaving(true);
    try {
      if (editingTerm) {
        // 更新现有术语 - 使用全局术语库
        await glossaryApi.updateGlobalTerm(editingTerm.original, {
          translation: editForm.translation || undefined,
          strategy: editForm.strategy,
          note: editForm.note || undefined,
        });
      } else {
        // 添加新术语 - 使用全局术语库
        await glossaryApi.addGlobalTerm({
          original: editForm.original,
          translation: editForm.translation || undefined,
          strategy: editForm.strategy,
          note: editForm.note || undefined,
        });
      }
      await loadGlossary();
      resetForm();
    } catch (error) {
      console.error('Failed to save term:', error);
    } finally {
      setIsSaving(false);
    }
  }, [editForm, editingTerm, loadGlossary, resetForm]);

  // 取消编辑
  const handleCancel = useCallback(() => {
    resetForm();
  }, [resetForm]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="术语库" size="xl">
      <div className="flex h-[600px]">
        {/* 左侧：术语列表 */}
        <div className="w-1/2 border-r border-border pr-4">
          {/* 搜索框 */}
          <div className="mb-4 relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索术语..."
              className={cn(
                'w-full rounded-lg border border-border pl-10 pr-4 py-2',
                'bg-bg-tertiary text-text-primary',
                'focus:outline-none focus:ring-2 focus:ring-primary-500',
                'placeholder:text-text-muted'
              )}
            />
          </div>

          {/* 术语统计 */}
          <div className="mb-3 flex items-center justify-between text-sm">
            <span className="text-text-secondary">
              共 {terms.length} 条术语
              {filteredTerms.length !== terms.length && `（显示 ${filteredTerms.length} 条）`}
            </span>
            <Button variant="secondary" size="sm" onClick={handleAdd} leftIcon={<Plus className="h-3 w-3" />}>
              添加
            </Button>
          </div>

          {/* 术语列表 */}
          <div className="space-y-2 overflow-y-auto pr-2" style={{ maxHeight: '480px' }}>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-text-secondary">加载中...</div>
              </div>
            ) : filteredTerms.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8">
                <BookOpen className="mb-2 h-10 w-10 text-text-muted" />
                <p className="text-text-secondary">
                  {searchQuery ? '没有找到匹配的术语' : '术语库为空'}
                </p>
              </div>
            ) : (
              filteredTerms.map((term) => (
                <div
                  key={term.original}
                  className={cn(
                    'group rounded-lg border p-3 transition-all',
                    editingTerm?.original === term.original
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 hover:bg-bg-tertiary/50'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-text-primary truncate">
                          {term.original}
                        </span>
                        <span
                          className={cn(
                            'rounded px-1.5 py-0.5 text-xs font-medium',
                            strategyColors[term.strategy]
                          )}
                        >
                          {strategyLabels[term.strategy]}
                        </span>
                      </div>
                      {term.translation && (
                        <p className="text-sm text-text-secondary truncate">{term.translation}</p>
                      )}
                      {term.note && (
                        <p className="mt-1 text-xs text-text-muted truncate">{term.note}</p>
                      )}
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleEdit(term)}
                        className="rounded p-1 text-text-secondary hover:text-primary hover:bg-primary/10"
                        title="编辑"
                      >
                        <Edit className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    {/* 全局术语库不支持删除 */}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 右侧：编辑表单 */}
        <div className="w-1/2 pl-4">
          {(isAdding || editingTerm) ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-text-primary">
                  {editingTerm ? '编辑术语' : '添加术语'}
                </h3>
                <button
                  onClick={handleCancel}
                  className="rounded p-1 text-text-secondary hover:text-text-primary hover:bg-bg-tertiary"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* 英文原文 */}
              <div>
                <label className="mb-2 block text-sm font-medium text-text-primary">
                  英文原文 *
                </label>
                <Input
                  value={editForm.original}
                  onChange={(e) => setEditForm({ ...editForm, original: e.target.value })}
                  placeholder="例如：foundry"
                  disabled={!!editingTerm}
                  className="w-full"
                />
              </div>

              {/* 中文翻译 */}
              <div>
                <label className="mb-2 block text-sm font-medium text-text-primary">
                  中文翻译
                </label>
                <Input
                  value={editForm.translation}
                  onChange={(e) => setEditForm({ ...editForm, translation: e.target.value })}
                  placeholder="例如：代工厂"
                  className="w-full"
                />
              </div>

              {/* 翻译策略 */}
              <div>
                <label className="mb-2 block text-sm font-medium text-text-primary">
                  翻译策略
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(strategyLabels).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setEditForm({ ...editForm, strategy: value as TranslationStrategy })}
                      className={cn(
                        'rounded-lg border px-3 py-2 text-sm transition-all',
                        editForm.strategy === value
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border text-text-secondary hover:border-primary/50'
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 备注 */}
              <div>
                <label className="mb-2 block text-sm font-medium text-text-primary">
                  备注
                </label>
                <textarea
                  value={editForm.note}
                  onChange={(e) => setEditForm({ ...editForm, note: e.target.value })}
                  placeholder="可选的备注说明..."
                  rows={3}
                  className={cn(
                    'w-full rounded-lg border border-border px-3 py-2',
                    'bg-bg-tertiary text-text-primary',
                    'focus:outline-none focus:ring-2 focus:ring-primary-500',
                    'placeholder:text-text-muted',
                    'resize-none'
                  )}
                />
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-3 pt-2">
                <Button variant="secondary" onClick={handleCancel} className="flex-1" disabled={isSaving}>
                  取消
                </Button>
                <Button
                  variant="primary"
                  onClick={handleSave}
                  disabled={!editForm.original.trim() || isSaving}
                  isLoading={isSaving}
                  leftIcon={<Check className="h-4 w-4" />}
                  className="flex-1"
                >
                  {isSaving ? '保存中...' : '保存'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex h-full flex-col items-center justify-center text-text-secondary">
              <BookOpen className="mb-3 h-12 w-12 text-text-muted" />
              <p>选择左侧术语进行编辑</p>
              <p className="mt-1 text-sm text-text-muted">或点击上方"添加"按钮新增术语</p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
