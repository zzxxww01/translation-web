import React, { useState } from 'react';
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
    <div className="refinement-panel">
      <div className="refinement-header">
        <h3>调整历史</h3>
        <button onClick={onClear} className="clear-btn">
          清除
        </button>
      </div>

      <div className="variants-list">
        {sortedVariants.map((variant, index) => (
          <div key={variant.id} className="variant-card">
            <div className="variant-header">
              <span className="variant-label">
                版本 {sortedVariants.length - index}
              </span>
              <span className="variant-time">
                {new Date(variant.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="variant-content">{variant.content}</div>
            <button
              onClick={() => onConfirm(variant.id)}
              className="confirm-btn"
            >
              ✓ 用这个
            </button>
          </div>
        ))}
      </div>

      <div className="refinement-input">
        <textarea
          value={instruction}
          onChange={e => setInstruction(e.target.value)}
          placeholder="输入调整指令，例如：更礼貌一些、语气更坚定..."
          disabled={session.isRefining}
          rows={2}
        />
        <button
          onClick={handleRefine}
          disabled={!instruction.trim() || session.isRefining}
          className="refine-btn"
        >
          {session.isRefining ? '调整中...' : '继续调整'}
        </button>
      </div>
    </div>
  );
};
