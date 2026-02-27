/**
 * 分段确认工作流 - 术语检测Hook
 */

import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { glossaryApi } from '../api/glossaryApi';
import type { TermChange, GlossaryTerm } from '../types';

/**
 * 使用术语检测
 */
export function useTermDetection(projectId: string) {
  // 加载项目术语表
  const { data: glossaryData, refetch: refetchGlossary } = useQuery({
    queryKey: ['glossary', projectId],
    queryFn: async () => {
      if (!projectId) return { terms: [] };

      try {
        return await glossaryApi.getProjectGlossary(projectId);
      } catch (error) {
        console.error('Failed to load glossary:', error);
        return { terms: [] };
      }
    },
    staleTime: 5 * 60 * 1000, // 5分钟
    enabled: !!projectId,
  });

  const glossary: GlossaryTerm[] = useMemo(
    () => glossaryData?.terms ?? [],
    [glossaryData?.terms]
  );

  /**
   * 提取译文中使用的术语
   */
  const extractTerms = useCallback(
    (text: string): Record<string, string> => {
      const used: Record<string, string> = {};

      glossary.forEach(term => {
        if (term.translation && text.includes(term.translation)) {
          used[term.original] = term.translation;
        }
      });

      return used;
    },
    [glossary]
  );

  /**
   * 匹配段落中的相关术语
   */
  const matchParagraphTerms = useCallback(
    async (paragraph: string, maxTerms = 20) => {
      if (!projectId) return [];

      try {
        const result = await glossaryApi.matchParagraphTerms(projectId, paragraph, maxTerms);
        return result.matches;
      } catch (error) {
        console.error('Failed to match terms:', error);
        return [];
      }
    },
    [projectId]
  );

  /**
   * 检测术语变更
   */
  const detectTermChanges = useCallback(
    async (original: string, edited: string): Promise<TermChange[]> => {
      const originalTerms = extractTerms(original);
      const editedTerms = extractTerms(edited);

      const changes: TermChange[] = [];

      for (const [term, translation] of Object.entries(originalTerms)) {
        if (editedTerms[term] && editedTerms[term] !== translation) {
          changes.push({
            term,
            old_translation: translation,
            new_translation: editedTerms[term],
          });
        }
      }

      return changes;
    },
    [extractTerms]
  );

  /**
   * 添加术语到术语库
   */
  const addTerm = useCallback(
    async (term: Omit<GlossaryTerm, 'first_occurrence'>) => {
      if (!projectId) return;

      try {
        await glossaryApi.addProjectTerm(projectId, {
          original: term.original,
          translation: term.translation || undefined,
          strategy: term.strategy,
          note: term.note || undefined,
        });
        await refetchGlossary();
      } catch (error) {
        console.error('Failed to add term:', error);
        throw error;
      }
    },
    [projectId, refetchGlossary]
  );

  /**
   * 更新术语
   */
  const updateTerm = useCallback(
    async (
      original: string,
      updates: Partial<Omit<GlossaryTerm, 'original' | 'first_occurrence'>>
    ) => {
      if (!projectId) return;

      try {
        await glossaryApi.updateProjectTerm(projectId, original, updates);
        await refetchGlossary();
      } catch (error) {
        console.error('Failed to update term:', error);
        throw error;
      }
    },
    [projectId, refetchGlossary]
  );

  /**
   * 删除术语
   */
  const deleteTerm = useCallback(
    async (original: string) => {
      if (!projectId) return;

      try {
        await glossaryApi.deleteProjectTerm(projectId, original);
        await refetchGlossary();
      } catch (error) {
        console.error('Failed to delete term:', error);
        throw error;
      }
    },
    [projectId, refetchGlossary]
  );

  return {
    glossary,
    detectTermChanges,
    extractTerms,
    matchParagraphTerms,
    addTerm,
    updateTerm,
    deleteTerm,
    refetchGlossary,
  };
}
