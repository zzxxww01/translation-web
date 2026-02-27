/**
 * 性能优化工具
 * 包含 memo、debounce、throttle 等工具函数
 */

import { useCallback, useEffect, useRef, useState } from 'react';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * 深度比较函数
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;

  if (a == null || b == null) return false;
  if (typeof a !== typeof b) return false;

  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    return a.every((item, i) => deepEqual(item, b[i]));
  }

  if (isRecord(a) && isRecord(b)) {
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);

    if (keysA.length !== keysB.length) return false;

    return keysA.every(key => deepEqual(a[key], b[key]));
  }

  return false;
}

/**
 * 防抖 Hook
 */
export function useDebounce<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callback(...args);
      }, delay);
    },
    [callback, delay]
  );
}

/**
 * 节流 Hook
 */
export function useThrottle<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const lastRunRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now();
      const timeSinceLastRun = now - lastRunRef.current;

      if (timeSinceLastRun >= delay) {
        callback(...args);
        lastRunRef.current = now;
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        timeoutRef.current = setTimeout(() => {
          callback(...args);
          lastRunRef.current = Date.now();
        }, delay - timeSinceLastRun);
      }
    },
    [callback, delay]
  );
}

/**
 * 上次值 Hook
 */
export function usePrevious<T>(value: T): T | undefined {
  const [previous, setPrevious] = useState<T | undefined>(undefined);
  const currentRef = useRef(value);

  useEffect(() => {
    setPrevious(currentRef.current);
    currentRef.current = value;
  }, [value]);

  return previous;
}

/**
 * 跟踪挂载状态 Hook
 */
export function useIsMounted(): () => boolean {
  const isMountedRef = useRef(true);
  const isMounted = useCallback(() => isMountedRef.current, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return isMounted;
}

/**
 * 安全的异步状态 Hook
 * 防止组件卸载后的状态更新
 */
export function useSafeAsync() {
  const isMounted = useIsMounted();

  const safeAsync = useCallback(
    async <T>(asyncFn: () => Promise<T>): Promise<T | undefined> => {
      try {
        const result = await asyncFn();
        if (isMounted()) {
          return result;
        }
      } catch (error) {
        if (isMounted()) {
          throw error;
        }
      }
      return undefined;
    },
    [isMounted]
  );

  return { safeAsync, isMounted };
}

/**
 * 批量更新状态 Hook
 */
export function useBatchUpdates<T extends Record<string, unknown>>(
  initialState: T,
  batchDelay = 100
) {
  const [state, setState] = useState<T>(initialState);
  const pendingUpdatesRef = useRef<Partial<T>>({});
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMounted = useIsMounted();

  const flushUpdates = useCallback(() => {
    if (!isMounted()) return;

    setState(prev => ({
      ...prev,
      ...pendingUpdatesRef.current,
    }));
    pendingUpdatesRef.current = {};
  }, [isMounted]);

  const batchUpdate = useCallback(
    (updates: Partial<T>) => {
      pendingUpdatesRef.current = {
        ...pendingUpdatesRef.current,
        ...updates,
      };

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(flushUpdates, batchDelay);
    },
    [batchDelay, flushUpdates]
  );

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return [state, batchUpdate] as const;
}
