import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button-extended';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

interface DiffOperation {
  type: 'equal' | 'delete' | 'insert';
  text: string;
}

interface TranslationComparisonProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (translation: string) => void;
  sourceText: string;
  originalTranslation: string;
  newTranslation: string;
  diffData: {
    operations: DiffOperation[];
    change_percentage: number;
  };
}

export const TranslationComparison: React.FC<TranslationComparisonProps> = ({
  isOpen,
  onClose,
  onSelect,
  sourceText,
  originalTranslation,
  newTranslation,
  diffData,
}) => {
  const [selectedVersion, setSelectedVersion] = useState<'original' | 'new'>('new');

  const handleConfirm = () => {
    const selected = selectedVersion === 'original' ? originalTranslation : newTranslation;
    onSelect(selected);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Choose translation version</DialogTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Change rate: {diffData.change_percentage.toFixed(1)}%
          </p>
        </DialogHeader>

        <div className="space-y-4 py-4 overflow-y-auto">
          <div>
            <p className="text-sm font-medium text-foreground mb-2">Source</p>
            <div className="p-3 bg-muted rounded-md text-sm text-muted-foreground">
              {sourceText}
            </div>
          </div>

          <Tabs value={selectedVersion} onValueChange={(v) => setSelectedVersion(v as 'original' | 'new')}>
            <TabsList className="w-full">
              <TabsTrigger value="original" className="flex-1">Current version</TabsTrigger>
              <TabsTrigger value="new" className="flex-1">New version</TabsTrigger>
            </TabsList>

            <TabsContent value="original">
              <div className="p-4 bg-background border-2 border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-blue-600">Current version</span>
                </div>
                <p className="text-sm text-foreground leading-relaxed">
                  {originalTranslation}
                </p>
              </div>
            </TabsContent>

            <TabsContent value="new">
              <div className="p-4 bg-background border-2 border-green-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-green-600">New version</span>
                </div>
                <p className="text-sm text-foreground leading-relaxed">
                  {newTranslation}
                </p>
              </div>
            </TabsContent>
          </Tabs>

          <div>
            <p className="text-sm font-medium text-foreground mb-2">Diff</p>
            <div className="p-4 bg-muted rounded-lg">
              <DiffView operations={diffData.operations} />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            variant={selectedVersion === 'new' ? 'default' : 'outline'}
          >
            {selectedVersion === 'original' ? 'Keep current version' : 'Use new version'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const DiffView: React.FC<{ operations: DiffOperation[] }> = ({ operations }) => {
  return (
    <div className="text-sm leading-relaxed">
      {operations.map((op, index) => {
        if (op.type === 'equal') {
          return (
            <span key={index} className="text-foreground">
              {op.text}
            </span>
          );
        }
        if (op.type === 'delete') {
          return (
            <span
              key={index}
              className="bg-red-100 text-red-800 line-through"
              title="Deleted"
            >
              {op.text}
            </span>
          );
        }
        if (op.type === 'insert') {
          return (
            <span
              key={index}
              className="bg-green-100 text-green-800 font-medium"
              title="Inserted"
            >
              {op.text}
            </span>
          );
        }
        return null;
      })}
    </div>
  );
};
