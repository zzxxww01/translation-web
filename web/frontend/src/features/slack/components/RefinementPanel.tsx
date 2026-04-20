import React, { useState } from 'react';
import { Check, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { RefinementSession } from '../types';

interface RefinementPanelProps {
  session: RefinementSession;
  onRefine: (instruction: string) => Promise<void>;
  onConfirm: (variantId: string) => void;
  onClear: () => void;
}

export const RefinementPanel: React.FC<RefinementPanelProps> = ({
  session,
  onRefine,
  onConfirm,
  onClear,
}) => {
  const [instruction, setInstruction] = useState('');

  const handleRefine = async () => {
    if (!instruction.trim()) return;
    await onRefine(instruction);
    setInstruction('');
  };

  const sortedVariants = [...session.variants].sort((a, b) => b.timestamp - a.timestamp);

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">调整历史</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClear}>
            <Trash2 className="h-3 w-3" />
            清除
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {sortedVariants.map((variant, index) => (
          <div key={variant.id} className="rounded-lg border bg-muted/30 p-3">
            <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium">版本 {sortedVariants.length - index}</span>
              <span>{new Date(variant.timestamp).toLocaleTimeString()}</span>
            </div>
            <div className="mb-3 whitespace-pre-wrap text-sm">{variant.content}</div>
            <Button
              size="sm"
              onClick={() => onConfirm(variant.id)}
              className="w-full"
            >
              <Check className="h-3 w-3 mr-1" />
              用这个版本
            </Button>
          </div>
        ))}

        <div className="space-y-2 pt-2 border-t">
          <Textarea
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            placeholder="输入调整指令，例如：更礼貌一些、语气更坚定..."
            disabled={session.isRefining}
            rows={2}
            className="text-sm"
          />
          <Button
            onClick={handleRefine}
            disabled={!instruction.trim() || session.isRefining}
            className="w-full"
            variant="secondary"
          >
            {session.isRefining ? (
              <>
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                调整中...
              </>
            ) : (
              '继续调整'
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
