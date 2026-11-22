// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { renameStorageKey } from './storageKeys';

describe('renameStorageKey', () => {
  afterEach(() => localStorage.clear());

  it('moves the old value to the new key', () => {
    localStorage.setItem('momo.x', '{"a":1}');
    renameStorageKey('momo.x', 'translation.x');
    expect(localStorage.getItem('translation.x')).toBe('{"a":1}');
    expect(localStorage.getItem('momo.x')).toBeNull();
  });

  it('keeps a value already saved under the new key', () => {
    localStorage.setItem('momo.x', 'old');
    localStorage.setItem('translation.x', 'new');
    renameStorageKey('momo.x', 'translation.x');
    expect(localStorage.getItem('translation.x')).toBe('new');
    expect(localStorage.getItem('momo.x')).toBeNull();
  });

  it('does nothing when there is no old value', () => {
    renameStorageKey('momo.x', 'translation.x');
    expect(localStorage.getItem('translation.x')).toBeNull();
  });
});
