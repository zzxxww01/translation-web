/**
 * 手动对齐参考译文模态框组件
 *
 * 用于处理未自动对齐的参考段落
 */



import { useState } from 'react';

import { Check, XCircle, ChevronRight } from 'lucide-react';

import { Modal } from '../../../components/ui/Modal';

import { Button } from '../../../components/ui';

import { cn } from '../../../shared/utils';

import type { UnalignedItem } from '../types';



interface AlignmentModalProps {

  isOpen: boolean;

  onClose: () => void;

  unalignedItems: UnalignedItem[];

  onAlign: (refIndex: number, targetParagraphId: string) => Promise<void>;

  onSkip: (refIndex: number) => Promise<void>;

  isProcessing?: boolean;

}



export function AlignmentModal({

  isOpen,

  onClose,

  unalignedItems,

  onAlign,

  onSkip,

  isProcessing = false,

}: AlignmentModalProps) {

  const [currentIndex, setCurrentIndex] = useState(0);

  const [selectedParagraphId, setSelectedParagraphId] = useState<string | null>(null);



  const currentItem = unalignedItems[currentIndex];



  const handleNext = () => {

    if (currentIndex < unalignedItems.length - 1) {

      setCurrentIndex(currentIndex + 1);

      setSelectedParagraphId(null);

    } else {

      onClose();

    }

  };



  const handleAlign = async () => {

    if (!selectedParagraphId) return;



    await onAlign(currentIndex, selectedParagraphId);

    handleNext();

  };



  const handleSkip = async () => {

    await onSkip(currentIndex);

    handleNext();

  };



  const handleSelectRecommendation = (paragraphId: string) => {

    setSelectedParagraphId(paragraphId);

  };



  if (!currentItem) {

    return null;

  }



  return (

    <Modal

      isOpen={isOpen}

      onClose={onClose}

      title="参考译文对齐"

      size="lg"

    >

      <div className="space-y-4 p-6">

        {/* 进度指示 */}

        <div className="mb-4">

          <div className="flex items-center justify-between text-sm">

            <span className="text-text-muted">

              待对齐段落

            </span>

            <span className="font-medium text-text-primary">

              {currentIndex + 1} / {unalignedItems.length}

            </span>

          </div>

          <div className="mt-2 h-2 w-full rounded-full bg-bg-tertiary">

            <div

              className="h-full rounded-full bg-primary-500 transition-all"

              style={{ width: `${((currentIndex + 1) / unalignedItems.length) * 100}%` }}

            />

          </div>

        </div>



        {/* 当前未对齐段落 */}

        <div>

          <label className="mb-2 block text-sm font-medium text-text-primary">

            参考译文段落 #{currentItem.ref_index + 1}

          </label>

          <div className="max-h-32 overflow-y-auto rounded-lg bg-bg-tertiary p-3">

            <p className="text-sm text-text-secondary whitespace-pre-wrap">

              {currentItem.ref_text}

            </p>

          </div>

        </div>



        {/* 相似度推荐 */}

        {currentItem.recommendations.length > 0 ? (

          <div>

            <label className="mb-3 block text-sm font-medium text-text-primary">

              相似度推荐

            </label>

            <div className="space-y-2 max-h-64 overflow-y-auto">

              {currentItem.recommendations.map((rec) => (

                <div

                  key={rec.paragraph_id}

                  className={cn(

                    'rounded-lg border-2 p-3 cursor-pointer transition-all',

                    selectedParagraphId === rec.paragraph_id

                      ? 'border-primary bg-primary/5'

                      : 'border-border hover:border-primary/50'

                  )}

                  onClick={() => handleSelectRecommendation(rec.paragraph_id)}

                >

                  <div className="flex items-start justify-between gap-3">

                    <div className="flex-1">

                      <div className="mb-1 flex items-center gap-2">

                        <span className="text-xs font-mono text-text-muted">

                          {rec.paragraph_id}

                        </span>

                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">

                          {rec.similarity}% 相似

                        </span>

                      </div>

                      <p className="text-sm text-text-secondary line-clamp-2">

                        {rec.source_preview}

                      </p>

                    </div>

                    {selectedParagraphId === rec.paragraph_id && (

                      <div className="flex-shrink-0">

                        <Check className="h-5 w-5 text-primary" />

                      </div>

                    )}

                  </div>

                </div>

              ))}

            </div>

          </div>

        ) : (

          <div className="rounded-lg bg-warning/10 p-4">

            <p className="text-sm text-warning">

              未找到相似的原文段落，建议跳过此段或手动选择。

            </p>

          </div>

        )}



        {/* 操作按钮 */}

        <div className="flex gap-3 pt-4 border-t border-border">

          <Button

            variant="secondary"

            onClick={handleSkip}

            disabled={isProcessing}

            leftIcon={<XCircle className="h-4 w-4" />}

            className="flex-1"

          >

            跳过

          </Button>

          <Button

            variant="primary"

            onClick={handleAlign}

            disabled={!selectedParagraphId || isProcessing}

            isLoading={isProcessing}

            leftIcon={<ChevronRight className="h-4 w-4" />}

            className="flex-1"

          >

            {currentIndex < unalignedItems.length - 1 ? '对齐并继续' : '对齐并完成'}

          </Button>

        </div>



        {/* 提示信息 */}

        <div className="rounded-lg bg-info/10 p-3">

          <p className="text-xs text-info">

            💡 选择最匹配的原文段落，然后点击"对齐并继续"。如果没有匹配的段落，可以选择"跳过"。

          </p>

        </div>

      </div>

    </Modal>

  );

}
