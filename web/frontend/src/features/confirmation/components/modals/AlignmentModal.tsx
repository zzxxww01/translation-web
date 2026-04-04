/**
 * 手动对齐参考译文模态框组件
 * 用于处理未自动对齐的参考段落
 */

import { useState } from 'react';
import { Check, XCircle, ChevronRight } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button-extended';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/shared/utils';
import type { UnalignedItem } from '../../types';

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

  const progressPercent = ((currentIndex + 1) / unalignedItems.length) * 100;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>参考译文对齐</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* 进度指示 */}
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-muted-foreground">待对齐段落</span>
              <span className="font-medium text-foreground">
                {currentIndex + 1} / {unalignedItems.length}
              </span>
            </div>
            <Progress value={progressPercent} className="h-2" />
          </div>

          {/* 当前未对齐段落 */}
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              参考译文段落 #{currentItem.ref_index + 1}
            </label>
            <div className="max-h-32 overflow-y-auto rounded-lg bg-muted p-3">
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {currentItem.ref_text}
              </p>
            </div>
          </div>

          {/* 相似度推荐 */}
          {currentItem.recommendations.length > 0 ? (
            <div>
              <label className="mb-3 block text-sm font-medium text-foreground">
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
                          <span className="text-xs font-mono text-muted-foreground">
                            {rec.paragraph_id}
                          </span>
                          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                            {rec.similarity}% 相似
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2">
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
            <div className="rounded-lg bg-yellow-50 p-4 dark:bg-yellow-950/30">
              <p className="text-sm text-yellow-600 dark:text-yellow-400">
                未找到相似的原文段落，建议跳过此段或手动选择。
              </p>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-3 pt-4 border-t border-border">
            <Button
              variant="outline"
              onClick={handleSkip}
              disabled={isProcessing}
              leftIcon={<XCircle className="h-4 w-4" />}
              className="flex-1"
            >
              跳过
            </Button>
            <Button
              variant="default"
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
          <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-950/30">
            <p className="text-xs text-blue-600 dark:text-blue-400">
              选择最匹配的原文段落，然后点击"对齐并继续"。如果没有匹配的段落，可以选择"跳过"。
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
