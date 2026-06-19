import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Loader2, Wand2, Send } from 'lucide-react';
import type { Instruction } from '../types';

const quickInstructions: Instruction[] = [
  { id: 'readable', label: '可读性', icon: '✨', instruction: '' },
  { id: 'idiomatic', label: '更地道', icon: '💬', instruction: '' },
  { id: 'professional', label: '专业化', icon: '👔', instruction: '' },
  { id: 'custom', label: '自定义', icon: '🔧', instruction: '' },
];

const moreInstructions: Instruction[] = [
  { id: 'shorten', label: '精简内容', icon: '✂️', instruction: '请精简译文内容，删除冗余表达，只保留核心信息和关键观点。' },
  { id: 'expand', label: '展开说明', icon: '📖', instruction: '请对译文中的关键点添加更多解释和背景信息，使内容更丰富。' },
  { id: 'formal', label: '正式公文', icon: '📜', instruction: '请将译文重写为正式公文风格，使用规范、严谨的官方表达。' },
  { id: 'story', label: '故事化', icon: '📖', instruction: '请用叙事方式重新组织译文内容，使其更具故事性和可读性。' },
  { id: 'qa', label: 'Q&A格式', icon: '❓', instruction: '请将译文转换为问答形式，先列出问题，然后给出答案。' },
  { id: 'social', label: '社交媒体', icon: '💬', instruction: '请将译文改写为适合社交媒体传播的风格，使用轻松活泼的表达，添加emoji。' },
];

interface OptimizationPanelProps {
  onOptimize: (options: { instruction?: string; optionId?: string }) => void;
  isLoading: boolean;
  isOptimizing: boolean;
  hasVersions: boolean;
  hasOriginal: boolean;
}

export function OptimizationPanel({ onOptimize, isLoading, isOptimizing, hasVersions, hasOriginal }: OptimizationPanelProps) {
  const [customInstruction, setCustomInstruction] = useState('');
  const [showMore, setShowMore] = useState(false);
  const disabled = isLoading || !hasOriginal || !hasVersions;

  const handleQuick = (id: string) => {
    if (id === 'custom') {
      document.getElementById('customInstructionInput')?.focus();
    } else {
      onOptimize({ optionId: id });
    }
  };

  const handleSendCustom = () => {
    if (customInstruction.trim()) {
      onOptimize({ instruction: customInstruction });
      setCustomInstruction('');
    }
  };

  return (
    <>
      <div className="rounded-xl border border-white/60 bg-white/85 p-4 shadow-sm backdrop-blur-sm">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-primary" />
            <h4 className="text-sm font-semibold">优化指令</h4>
          </div>

          <div className="flex flex-wrap gap-2">
            {quickInstructions.map(inst => (
              <Button
                key={inst.id}
                variant="outline"
                size="sm"
                onClick={() => handleQuick(inst.id)}
                disabled={disabled}
                className="min-h-10 px-3 text-sm sm:min-h-9 sm:text-xs"
              >
                {inst.icon} {inst.label}
              </Button>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowMore(true)}
              disabled={disabled}
              className="min-h-10 border-dashed px-3 text-sm sm:min-h-9 sm:text-xs"
            >
              更多...
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Input
              id="customInstructionInput"
              placeholder="优化要求..."
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendCustom()}
              disabled={isLoading}
              className="h-10 min-w-0 flex-1"
            />
            <Button
              size="sm"
              onClick={handleSendCustom}
              disabled={!hasVersions || !customInstruction.trim() || isLoading}
              title="发送指令 (Ctrl+K)"
              className="h-10 w-10 shrink-0 p-0"
            >
              {isOptimizing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>

      <Dialog open={showMore} onOpenChange={setShowMore}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>更多优化指令</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {moreInstructions.map(inst => (
              <Button
                key={inst.id}
                variant="outline"
                onClick={() => { setShowMore(false); onOptimize({ instruction: inst.instruction }); }}
                disabled={isLoading}
                className="h-auto min-h-16 flex-row justify-start gap-3 py-3 text-left sm:min-h-20 sm:flex-col sm:justify-center sm:gap-2 sm:py-4"
              >
                <span className="text-xl sm:text-2xl">{inst.icon}</span>
                <span className="text-sm">{inst.label}</span>
              </Button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
