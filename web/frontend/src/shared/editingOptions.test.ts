import { describe, it, expect } from 'vitest';
import { EDITING_OPTIONS, EDITING_OPTION_VERSION, getEditingInstruction } from './editingOptions';
import { describeOptimizeOption } from '../features/post/types';

describe('shared edit policy', () => {
  it.each(['readable', 'idiomatic', 'professional'])('uses one versioned instruction for %s', id => {
    const item = EDITING_OPTIONS.find(option => option.id === id);
    expect(item).toBeDefined();
    expect(getEditingInstruction(id)).toBe(item?.instruction);
    expect(describeOptimizeOption(id)).toContain(EDITING_OPTION_VERSION);
  });
  it('does not reinstate the old connector ban', () => {
    expect(getEditingInstruction('idiomatic')).not.toContain('删连接词');
    expect(getEditingInstruction('unknown')).toBe('');
  });
});
