/**
 * 长文翻译相关的 React Query hooks
 * 提供统一的数据获取和状态管理
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { documentApi } from './api';
import type { WordMeaningMessage } from './api';
import { useDocumentStore } from '../../shared/stores';
import { useToast } from '../../components/ui';
import { useErrorHandler } from '../../shared/hooks/useErrorHandler';
import { DEFAULT_STALE_TIME, ParagraphStatus } from '../../shared/constants';
import type { CreateProjectDto, Section } from '../../shared/types';
import { fullTranslationService, type TranslationMethodType } from './services/fullTranslationService';

/**
 * 获取项目列表
 */
export function useProjects() {
  const { handleError } = useErrorHandler();

  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      try {
        return await documentApi.getProjects();
      } catch (error) {
        handleError(error, '获取项目列表失败');
        throw error;
      }
    },
    staleTime: DEFAULT_STALE_TIME,
  });
}

/**
 * 获取单个项目
 */
export function useProject(projectId: string) {
  const { setCurrentProject, setSections } = useDocumentStore();
  const { handleError } = useErrorHandler();

  return useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      try {
        const project = await documentApi.getProject(projectId);
        setCurrentProject(project);
        setSections(project.sections ?? []);
        return project;
      } catch (error) {
        handleError(error, '获取项目详情失败');
        throw error;
      }
    },
    enabled: !!projectId,
  });
}

/**
 * 创建项目
 */
export function useCreateProject() {
  const queryClient = useQueryClient();
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: async (data: CreateProjectDto | FormData) => {
      try {
        // 如果是FormData，使用文件上传
        if (data instanceof FormData) {
          return await documentApi.uploadProject(data);
        }
        // 否则使用普通创建
        return await documentApi.createProject(data);
      } catch (error) {
        handleError(error, '创建项目失败');
        throw error;
      }
    },
    onSuccess: result => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      showSuccess('项目创建成功！');
      return result;
    },
    onError: error => {
      handleError(error, '创建项目失败');
    },
  });
}

/**
 * 获取章节
 */
export function useSection(projectId: string, sectionId: string) {
  const { setCurrentSection } = useDocumentStore();
  const { handleError } = useErrorHandler();

  return useQuery({
    queryKey: ['section', projectId, sectionId],
    queryFn: async () => {
      try {
        const section = await documentApi.getSection(projectId, sectionId);
        setCurrentSection(section);
        return section;
      } catch (error) {
        handleError(error, '获取章节失败');
        throw error;
      }
    },
    enabled: !!projectId && !!sectionId,
  });
}

/**
 * 翻译段落
 */
export function useTranslateParagraph() {
  const queryClient = useQueryClient();
  const updateParagraphInSection = useDocumentStore(state => state.updateParagraphInSection);
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({
      projectId,
      sectionId,
      paragraphId,
      instruction,
      model,
    }: {
      projectId: string;
      sectionId: string;
      paragraphId: string;
      instruction?: string;
      model?: string;
    }) => documentApi.translateParagraph(projectId, sectionId, paragraphId, instruction, model),
    onSuccess: (result, variables) => {
      const updates = {
        translation: result.translation,
        status: result.status ?? ParagraphStatus.TRANSLATED,
        confirmed:
          result.confirmed ??
          (result.status === ParagraphStatus.APPROVED ? result.translation : undefined),
      };

      updateParagraphInSection(variables.sectionId, variables.paragraphId, updates);
      queryClient.setQueryData<Section | undefined>(
        ['section', variables.projectId, variables.sectionId],
        previous => {
          if (!previous?.paragraphs) return previous;
          return {
            ...previous,
            paragraphs: previous.paragraphs.map(paragraph =>
              paragraph.id === variables.paragraphId ? { ...paragraph, ...updates } : paragraph
            ),
          };
        }
      );

      showSuccess('翻译完成！');
      return result;
    },
    onError: error => {
      handleError(error, '翻译失败');
    },
  });
}

/**
 * 查询词义（编辑译文面板）
 */
export function useQueryWordMeaning() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({
      projectId,
      sectionId,
      paragraphId,
      word,
      query,
      history,
      model,
    }: {
      projectId: string;
      sectionId: string;
      paragraphId: string;
      word: string;
      query: string;
      history?: WordMeaningMessage[];
      model?: string;
    }) =>
      documentApi.queryWordMeaning(
        projectId,
        sectionId,
        paragraphId,
        word,
        query,
        history ?? [],
        model
      ),
    onError: error => {
      handleError(error, '词义查询失败');
    },
  });
}

/**
 * 确认段落翻译
 */
export function useConfirmParagraph() {
  const queryClient = useQueryClient();
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({
      projectId,
      sectionId,
      paragraphId,
      translation,
    }: {
      projectId: string;
      sectionId: string;
      paragraphId: string;
      translation: string;
    }) => documentApi.confirmParagraph(projectId, sectionId, paragraphId, translation),
    onSuccess: (_data, variables) => {
      // 刷新章节数据（更新段落状态）
      queryClient.invalidateQueries({ queryKey: ['section', variables.projectId, variables.sectionId] });
      // 刷新项目列表（更新进度）
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      // 刷新当前项目详情
      queryClient.invalidateQueries({ queryKey: ['project', variables.projectId] });
      showSuccess('译文已确认 ✓');
    },
    onError: error => {
      handleError(error, '确认翻译失败');
    },
  });
}

/**
 * 分析项目
 */
export function useAnalyzeProject() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (projectId: string) => documentApi.analyzeProject(projectId),
    onSuccess: () => {
      showSuccess('分析完成');
    },
    onError: error => {
      handleError(error, '项目分析失败');
    },
  });
}

/**
 * 分析章节
 */
export function useAnalyzeSection() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({ projectId, sectionId }: { projectId: string; sectionId: string }) =>
      documentApi.analyzeSection(projectId, sectionId),
    onSuccess: () => {
      showSuccess('分析完成');
    },
    onError: error => {
      handleError(error, '章节分析失败');
    },
  });
}

/**
 * 批量翻译章节
 */
export function useBatchTranslate() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({ projectId, sectionId }: { projectId: string; sectionId: string }) =>
      documentApi.batchTranslate(projectId, sectionId),
    onSuccess: result => {
      showToast(`翻译完成！共翻译 ${result.translated_count} 个段落`, 'success');
      queryClient.invalidateQueries({ queryKey: ['section'] });
    },
    onError: error => {
      handleError(error, '批量翻译失败');
    },
  });
}

/**
 * 导出项目
 */
export function useExportProject() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({ projectId, format }: { projectId: string; format?: 'markdown' | 'html' }) =>
      documentApi.exportProject(projectId, format),
    onSuccess: (result) => {
      // 创建下载链接
      const blob = new Blob([result.content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `output.${result.format === 'html' ? 'html' : 'md'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      showSuccess(`已导出 ${result.format === 'html' ? 'HTML' : 'Markdown'} 文件`);
    },
    onError: error => {
      handleError(error, '导出失败');
    },
  });
}

/**
 * 全文一键翻译 (SSE 流式，使用单例服务保持跨tab状态)
 * 支持选择翻译方法：普通翻译或四步法翻译
 */
export function useFullTranslate() {
  const { showToast } = useToast();
  const { handleError } = useErrorHandler();
  const queryClient = useQueryClient();
  const updateParagraphInSection = useDocumentStore(state => state.updateParagraphInSection);

  // Store actions for full translation state
  const setFullTranslating = useDocumentStore(state => state.setFullTranslating);
  const setFullTranslateProgress = useDocumentStore(state => state.setFullTranslateProgress);
  const setFullTranslateProjectId = useDocumentStore(state => state.setFullTranslateProjectId);
  const endFullTranslate = useDocumentStore(state => state.endFullTranslate);

  const startTranslation = async (
    projectId: string,
    onProgress: (data: {
      type: string;
      current?: number;
      total?: number;
      translated_count?: number;
      paragraph_id?: string;
      section_id?: string;
      translation?: string;
      error?: string;
      step?: string;
      message?: string;
    }) => void,
    onComplete: () => void,
    model?: string,
    method: TranslationMethodType = 'normal'
  ) => {
    // 开始翻译，设置初始状态
    setFullTranslateProjectId(projectId);
    setFullTranslating(true);
    setFullTranslateProgress({ current: 0, total: 0 });

    try {
      // 使用单例服务启动翻译
      await fullTranslationService.startTranslation(
        projectId,
        (data) => {
          // 处理开始事件，更新 total
          if (data.type === 'start' && data.total) {
            setFullTranslateProgress({ current: 0, total: data.total });
          }

          // 实时更新：当收到翻译结果时，立即更新 store
          if (data.type === 'translated' && data.paragraph_id && data.section_id && data.translation) {
            updateParagraphInSection(data.section_id, data.paragraph_id, {
              translation: data.translation,
              status: ParagraphStatus.TRANSLATED,
            });
          }

          // 更新进度
          if (data.type === 'translated' || data.type === 'skip' || data.type === 'error') {
            if (data.current !== undefined && data.total !== undefined) {
              setFullTranslateProgress({ current: data.current, total: data.total });
            }
          }

          // 调用外部进度回调
          onProgress(data);

          if (data.type === 'complete') {
            const translatedCount = (data as { translated_count?: number }).translated_count || 0;
            const methodLabel = method === 'four-step' ? '四步法翻译' : '翻译';
            showToast(`${methodLabel}完成！共翻译 ${translatedCount} 个段落`, 'success');
            // 刷新查询以确保数据同步
            queryClient.invalidateQueries({ queryKey: ['section'] });
            queryClient.invalidateQueries({ queryKey: ['project'] });
            // 结束翻译状态
            endFullTranslate();
            onComplete();
          }
        },
        () => {
          // 完成回调
          endFullTranslate();
          onComplete();
        },
        model,
        method
      );
    } catch (error) {
      handleError(error, '全文翻译失败');
      endFullTranslate();
      onComplete();
    }
  };

  const stopTranslation = () => {
    fullTranslationService.stopTranslation();
    endFullTranslate();
  };

  return {
    startTranslation,
    stopTranslation,
    // 获取当前翻译状态
    isTranslating: () => fullTranslationService.isTranslating(),
    getProjectId: () => fullTranslationService.getProjectId(),
    getProgress: () => fullTranslationService.getProgress(),
    getModel: () => fullTranslationService.getModel(),
    getMethod: () => fullTranslationService.getMethod(),
  };
}
