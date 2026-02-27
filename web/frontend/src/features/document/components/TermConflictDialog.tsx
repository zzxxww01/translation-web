/**
 * 术语冲突确认对话框（方案 C 新增）
 *
 * 当检测到同一术语有不同翻译建议时，暂停翻译让用户确认。
 */

import React, { useState } from 'react';

interface TermConflictDialogProps {
  open: boolean;
  term: string;
  existingTranslation: string;
  existingContext: string;
  newTranslation: string;
  newContext: string;
  existingSectionId?: string;
  newSectionId?: string;
  onResolve: (chosenTranslation: string, applyToAll: boolean) => void;
  onClose: () => void;
}

export const TermConflictDialog: React.FC<TermConflictDialogProps> = ({
  open,
  term,
  existingTranslation,
  existingContext,
  newTranslation,
  newContext,
  existingSectionId,
  newSectionId,
  onResolve,
  onClose,
}) => {
  const [customTranslation, setCustomTranslation] = useState('');
  const [applyToAll, setApplyToAll] = useState(true);
  const [selectedOption, setSelectedOption] = useState<'existing' | 'new' | 'custom'>('existing');

  if (!open) return null;

  const handleResolve = () => {
    let chosenTranslation = '';
    switch (selectedOption) {
      case 'existing':
        chosenTranslation = existingTranslation;
        break;
      case 'new':
        chosenTranslation = newTranslation;
        break;
      case 'custom':
        chosenTranslation = customTranslation;
        break;
    }
    onResolve(chosenTranslation, applyToAll);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-yellow-50 border-b border-yellow-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h2 className="text-lg font-semibold text-gray-900">术语翻译冲突</h2>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {/* Term */}
          <div className="text-center">
            <span className="text-sm text-gray-500">术语</span>
            <p className="text-xl font-mono font-bold text-blue-600">{term}</p>
          </div>

          {/* Options */}
          <div className="space-y-3">
            {/* Existing translation */}
            <label className={`block p-4 border rounded-lg cursor-pointer transition-colors ${
              selectedOption === 'existing' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
            }`}>
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  name="translation"
                  checked={selectedOption === 'existing'}
                  onChange={() => setSelectedOption('existing')}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{existingTranslation}</span>
                    <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">已有翻译</span>
                  </div>
                  {existingContext && (
                    <p className="mt-1 text-sm text-gray-500">
                      上下文: {existingContext}
                    </p>
                  )}
                  {existingSectionId && (
                    <p className="mt-1 text-xs text-gray-400">
                      首次出现于: {existingSectionId}
                    </p>
                  )}
                </div>
              </div>
            </label>

            {/* New translation */}
            <label className={`block p-4 border rounded-lg cursor-pointer transition-colors ${
              selectedOption === 'new' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
            }`}>
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  name="translation"
                  checked={selectedOption === 'new'}
                  onChange={() => setSelectedOption('new')}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{newTranslation}</span>
                    <span className="text-xs px-2 py-0.5 bg-green-100 text-green-600 rounded">新建议</span>
                  </div>
                  {newContext && (
                    <p className="mt-1 text-sm text-gray-500">
                      上下文: {newContext}
                    </p>
                  )}
                  {newSectionId && (
                    <p className="mt-1 text-xs text-gray-400">
                      出现于: {newSectionId}
                    </p>
                  )}
                </div>
              </div>
            </label>

            {/* Custom translation */}
            <label className={`block p-4 border rounded-lg cursor-pointer transition-colors ${
              selectedOption === 'custom' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
            }`}>
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  name="translation"
                  checked={selectedOption === 'custom'}
                  onChange={() => setSelectedOption('custom')}
                  className="mt-1"
                />
                <div className="flex-1">
                  <span className="font-medium text-gray-900">自定义翻译</span>
                  {selectedOption === 'custom' && (
                    <input
                      type="text"
                      value={customTranslation}
                      onChange={(e) => setCustomTranslation(e.target.value)}
                      placeholder="输入自定义翻译..."
                      className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                    />
                  )}
                </div>
              </div>
            </label>
          </div>

          {/* Apply to all checkbox */}
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={applyToAll}
              onChange={(e) => setApplyToAll(e.target.checked)}
              className="rounded"
            />
            <span>应用到所有已翻译的段落</span>
          </label>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            跳过
          </button>
          <button
            onClick={handleResolve}
            disabled={selectedOption === 'custom' && !customTranslation.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            确认并继续
          </button>
        </div>
      </div>
    </div>
  );
};

export default TermConflictDialog;
