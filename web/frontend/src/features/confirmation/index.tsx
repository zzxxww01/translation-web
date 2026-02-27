/**

 * 分段确认工作流 - 主入口组件

 *

 * 这是分段确认工作流的主要组件，负责：

 * 1. 初始化工作流

 * 2. 显示原文和版本列表

 * 3. 处理用户交互

 * 4. 管理导航和导出

 */



import { useEffect, useCallback, useState } from 'react';

import { Upload } from 'lucide-react';

import { useConfirmationWorkflow } from './hooks/useConfirmationWorkflow';

import { useConfirmationStore } from './stores/confirmationStore';

import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

import { SourcePanel } from './components/SourcePanel';

import { VersionsPanel } from './components/VersionsPanel';

import { ProgressBar } from './components/ProgressBar';

import { NavigationControls } from './components/NavigationControls';

import { ImportVersionModal } from './components/ImportVersionModal';

import { AlignmentModal } from './components/AlignmentModal';

import { Button } from '../../components/ui';

import { cn } from '../../shared/utils';

import { confirmationApi } from './api/confirmationApi';
import type { UnalignedItem } from './types';



interface ConfirmationFeatureProps {

  projectId: string;

  onComplete?: () => void;

  className?: string;

}



export function ConfirmationFeature({

  projectId,

  onComplete,

  className,

}: ConfirmationFeatureProps) {

  const {

    workflowStatus,

    currentIndex,

    isLoading,

    error,

    currentParagraph,
    totalParagraphs,

    initialize,

    loadParagraph,

    selectVersion,

    confirmParagraph,

    exportTranslation,

    importReferenceVersion,

    nextParagraph,

    prevParagraph,

    jumpTo,

  } = useConfirmationWorkflow();



  const { customTranslation } = useConfirmationStore();



  // 模态框状态

  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const [isAlignmentModalOpen, setIsAlignmentModalOpen] = useState(false);

  const [unalignedItems, setUnalignedItems] = useState<UnalignedItem[]>([]);

  const [isImporting, setIsImporting] = useState(false);

  const [isAligning, setIsAligning] = useState(false);



  // 重新翻译状态

  const [isRetranslating, setIsRetranslating] = useState(false);



  // 初始化工作流

  useEffect(() => {

    initialize(projectId);

  }, [projectId, initialize]);



  // 加载当前段落

  useEffect(() => {

    if (workflowStatus === 'ready' && totalParagraphs > 0) {

      loadParagraph(currentIndex);

    }

  }, [workflowStatus, currentIndex, totalParagraphs, loadParagraph]);



  // 键盘快捷键

  useKeyboardShortcuts({

    onConfirm: () => {

      if (customTranslation.trim()) {

        confirmParagraph(customTranslation, undefined, true);

      }

    },

    onNext: nextParagraph,

    onPrev: prevParagraph,

  });



  // 选择版本

  const handleSelectVersion = useCallback(

    (versionId: string) => {

      selectVersion(versionId);

    },

    [selectVersion]

  );



  // 编辑版本

  const handleEditVersion = useCallback(

    (version: { id: string; translation: string }) => {

      selectVersion(version.id);

    },

    [selectVersion]

  );



  // 重新翻译段落

  const handleRetranslate = useCallback(

    async (instruction: string) => {

      if (!currentParagraph) return;



      setIsRetranslating(true);

      try {

        await confirmationApi.retranslateParagraph(

          projectId,

          currentParagraph.id,

          instruction

        );



        // 重新加载当前段落以获取新版本

        await loadParagraph(currentIndex);

      } catch (error) {

        console.error('重新翻译失败:', error);

      } finally {

        setIsRetranslating(false);

      }

    },

    [currentParagraph, currentIndex, loadParagraph, projectId]

  );



  // 确认译文

  const handleConfirm = useCallback(

    async (translation: string) => {

      await confirmParagraph(translation);



      // 检查是否完成

      if (currentIndex >= totalParagraphs - 1) {

        onComplete?.();

      }

    },

    [confirmParagraph, currentIndex, totalParagraphs, onComplete]

  );



  // 导出译文

  const handleExport = useCallback(async () => {

    await exportTranslation();

  }, [exportTranslation]);



  // 导入参考译文

  const handleImportReference = useCallback(

    async (versionName: string, markdownContent: string) => {

      setIsImporting(true);

      try {

        const result = await importReferenceVersion(versionName, markdownContent);



        // 如果有未对齐的段落，显示对齐模态框

        if (result && result.unaligned_count > 0 && result.unaligned_items?.length > 0) {

          setUnalignedItems(result.unaligned_items);

          setIsAlignmentModalOpen(true);

        } else {

          // 导入完成，重新加载当前段落

          await loadParagraph(currentIndex);

        }



        setIsImportModalOpen(false);

      } catch (error) {

        console.error('Import failed:', error);

        throw error;

      } finally {

        setIsImporting(false);

      }

    },

    [importReferenceVersion, currentIndex, loadParagraph]

  );



  // 手动对齐

  const handleManualAlign = useCallback(

    async (_refIndex: number, _targetParagraphId: string) => {

      setIsAligning(true);

      try {

        // 调用对齐API（需要在workflow hook中实现）

        // await confirmationApi.manualAlign(projectId, versionId, { refIndex, targetParagraphId });

        // 临时处理

        await new Promise((resolve) => setTimeout(resolve, 500));

      } catch (error) {

        console.error('Align failed:', error);

      } finally {

        setIsAligning(false);

      }

    },
    []
  );



  // 跳过未对齐段落

  const handleSkipUnaligned = useCallback(

    async (_refIndex: number) => {

      setIsAligning(true);

      try {

        // 调用跳过API

        // await confirmationApi.skipUnaligned(projectId, versionId, refIndex);

        await new Promise((resolve) => setTimeout(resolve, 500));

      } catch (error) {

        console.error('Skip failed:', error);

      } finally {

        setIsAligning(false);

      }

    },
    []
  );



  // 加载状态

  if (workflowStatus === 'loading' || isLoading) {

    return (

      <div className={cn('flex h-screen items-center justify-center', className)}>

        <div className="text-center">

          <div className="mb-4">

            <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />

          </div>

          <p className="text-lg font-medium text-text-primary">正在初始化工作流...</p>

        </div>

      </div>

    );

  }



  // 翻译中状态

  if (workflowStatus === 'translating') {

    return (

      <div className={cn('flex h-screen items-center justify-center', className)}>

        <div className="text-center max-w-md">

          <div className="mb-6">

            <div className="inline-block h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent" />

          </div>

          <h2 className="text-2xl font-bold text-text-primary mb-2">正在翻译中...</h2>

          <p className="text-text-secondary">

            使用四步法翻译所有段落，请稍候

          </p>

          <div className="mt-6 p-4 bg-muted rounded-lg">

            <div className="text-sm text-text-secondary">

              四步法包括：理解 → 翻译 → 反思 → 润色

            </div>

          </div>

        </div>

      </div>

    );

  }



  // 错误状态

  if (error) {

    return (

      <div className={cn('flex h-screen items-center justify-center', className)}>

        <div className="text-center max-w-md">

          <div className="mb-4 text-6xl" role="img" aria-label="error">

            ⚠️

          </div>

          <h2 className="text-2xl font-bold text-text-primary mb-2">出错了</h2>

          <p className="text-text-secondary mb-6">{error}</p>

          <Button onClick={() => initialize(projectId)}>重试</Button>

        </div>

      </div>

    );

  }



  // 完成状态

  if (workflowStatus === 'complete') {

    return (

      <div className={cn('flex h-screen items-center justify-center', className)}>

        <div className="text-center max-w-md">

          <div className="mb-4 text-6xl" role="img" aria-label="success">

            🎉

          </div>

          <h2 className="text-2xl font-bold text-text-primary mb-2">全部完成！</h2>

          <p className="text-text-secondary mb-6">

            所有段落已确认完成，您可以导出译文了

          </p>

          <div className="flex gap-3 justify-center">

            <Button variant="primary" onClick={handleExport}>

              导出译文

            </Button>

            <Button variant="secondary" onClick={onComplete}>

              返回

            </Button>

          </div>

        </div>

      </div>

    );

  }



  // 主界面

  return (

    <div className={cn('flex h-screen bg-background', className)}>

      {/* 左侧原文面板 (30%) */}

      <SourcePanel paragraph={currentParagraph} projectId={projectId} />



      {/* 右侧版本面板 (70%) */}

      <div className="flex-1 flex flex-col">

        {/* 顶部进度条和导航 */}

        <div className="border-b border-border bg-card p-4">

          <div className="flex items-center justify-between">

            <div className="flex-1 mr-6">

              <ProgressBar

                current={currentIndex + 1}

                total={totalParagraphs}

                onJump={jumpTo}

              />

            </div>



            <NavigationControls

              currentIndex={currentIndex}

              total={totalParagraphs}

              onPrev={prevParagraph}

              onNext={nextParagraph}

            />



            <div className="flex gap-2 ml-6">

              <Button

                variant="secondary"

                onClick={() => setIsImportModalOpen(true)}

                leftIcon={<Upload className="h-4 w-4" />}

              >

                导入参考

              </Button>

              <Button variant="secondary" onClick={onComplete}>

                返回

              </Button>

              <Button variant="primary" onClick={handleExport}>

                导出译文

              </Button>

            </div>

          </div>

        </div>



        {/* 版本列表 */}

        <VersionsPanel
          onSelectVersion={handleSelectVersion}

          onEditVersion={handleEditVersion}

          onConfirm={handleConfirm}

          onRetranslate={handleRetranslate}

          isRetranslating={isRetranslating}

        />

      </div>



      {/* 导入参考译文模态框 */}

      <ImportVersionModal

        isOpen={isImportModalOpen}

        onClose={() => setIsImportModalOpen(false)}

        onImport={handleImportReference}

        isImporting={isImporting}

      />



      {/* 手动对齐模态框 */}

      <AlignmentModal

        isOpen={isAlignmentModalOpen}

        onClose={() => setIsAlignmentModalOpen(false)}

        unalignedItems={unalignedItems}

        onAlign={handleManualAlign}

        onSkip={handleSkipUnaligned}

        isProcessing={isAligning}

      />

    </div>

  );

}



