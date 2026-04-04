import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button-extended';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';

interface RetranslateDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onRetranslate: (option: string, customInstruction?: string) => void;
  sourceText: string;
  currentTranslation: string;
}

export const RetranslateDialog: React.FC<RetranslateDialogProps> = ({
  isOpen,
  onClose,
  onRetranslate,
  sourceText,
  currentTranslation,
}) => {
  const [selectedOption, setSelectedOption] = useState<string>('rewrite');
  const [customInstruction, setCustomInstruction] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  const options = [
    {
      value: 'rewrite',
      label: '重写（增加流畅性和可读性）',
      description: '重新组织语言，让译文更自然流畅',
      isDefault: true,
    },
    {
      value: 'concise',
      label: '更简洁',
      description: '删除冗余词汇，使表达更精炼',
      isDefault: false,
    },
    {
      value: 'professional',
      label: '更专业',
      description: '采用学术化或技术化的语言风格',
      isDefault: false,
    },
  ];

  const handleRetranslate = async () => {
    setIsLoading(true);
    try {
      await onRetranslate(selectedOption, customInstruction || undefined);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>重新翻译</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* 原文预览 */}
          <div>
            <Label className="text-sm font-medium">原文</Label>
            <div className="mt-2 p-3 bg-muted rounded-md text-sm text-muted-foreground max-h-24 overflow-y-auto">
              {sourceText}
            </div>
          </div>

          {/* 当前译文 */}
          <div>
            <Label className="text-sm font-medium">当前译文</Label>
            <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-md text-sm text-foreground max-h-24 overflow-y-auto">
              {currentTranslation}
            </div>
          </div>

          {/* 翻译选项 */}
          <div>
            <Label className="text-sm font-medium mb-3 block">
              选择优化方式
            </Label>
            <RadioGroup value={selectedOption} onValueChange={setSelectedOption}>
              <div className="space-y-3">
                {options.map((option) => (
                  <div
                    key={option.value}
                    className="flex items-start space-x-3 p-3 rounded-lg hover:bg-accent transition-colors"
                  >
                    <RadioGroupItem value={option.value} id={option.value} className="mt-1" />
                    <div className="flex-1">
                      <Label
                        htmlFor={option.value}
                        className="text-sm font-medium cursor-pointer"
                      >
                        {option.label}
                        {option.isDefault && (
                          <span className="ml-2 text-xs text-blue-600">（默认）</span>
                        )}
                      </Label>
                      <p className="text-xs text-muted-foreground mt-1">{option.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </RadioGroup>
          </div>

          {/* 自定义说明 */}
          <div>
            <Label htmlFor="custom-instruction" className="text-sm font-medium">
              或补充说明（可选）
            </Label>
            <Textarea
              id="custom-instruction"
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              placeholder='例如："减少专业术语"、"使表达更口语化"'
              className="mt-2"
              rows={3}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              自定义说明会在所选方式的基础上额外应用
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            取消
          </Button>
          <Button onClick={handleRetranslate} disabled={isLoading}>
            {isLoading ? '生成中...' : '生成新版本'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
