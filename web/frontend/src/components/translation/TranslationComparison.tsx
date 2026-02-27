import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/Dialog';
import { Button } from '../ui/Button';
import { Tabs } from '../ui/Tabs';

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
  const tabs = [
    { id: 'original', label: 'Current version' },
    { id: 'new', label: 'New version ?' },
  ];

  const handleConfirm = () => {
    const selected = selectedVersion === 'original' ? originalTranslation : newTranslation;
    onSelect(selected);
    onClose();
  };

  return (
    <Dialog open={isOpen} onClose={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Choose translation version</DialogTitle>
          <p className="text-sm text-gray-500 mt-1">
            Change rate: {diffData.change_percentage.toFixed(1)}%
          </p>
        </DialogHeader>

        <div className="space-y-4 py-4 overflow-y-auto">
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Source</p>
            <div className="p-3 bg-gray-50 rounded-md text-sm text-gray-600">
              {sourceText}
            </div>
          </div>

          <Tabs
            tabs={tabs}
            activeTab={selectedVersion}
            onChange={(v) => setSelectedVersion(v as 'original' | 'new')}
            variant="segmented"
            size="sm"
            className="w-full"
          />

          {selectedVersion === 'original' && (
            <div className="mt-4 p-4 bg-white border-2 border-blue-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-blue-600">Current version</span>
              </div>
              <p className="text-sm text-gray-800 leading-relaxed">
                {originalTranslation}
              </p>
            </div>
          )}

          {selectedVersion === 'new' && (
            <div className="mt-4 p-4 bg-white border-2 border-green-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-green-600">New version</span>
              </div>
              <p className="text-sm text-gray-800 leading-relaxed">
                {newTranslation}
              </p>
            </div>
          )}

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Diff</p>
            <div className="p-4 bg-gray-50 rounded-lg">
              <DiffView operations={diffData.operations} />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            variant={selectedVersion === 'new' ? 'primary' : 'secondary'}
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
            <span key={index} className="text-gray-800">
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
