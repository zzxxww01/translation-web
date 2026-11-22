/**
 * 2026-11-23 起网站改称「翻译服务」，本地存储的键名从 momo.* 换成 translation.*。
 * 模块加载时把旧键的值搬到新键（新键已有值就不动），已经记住的偏好不会丢。
 */
export function renameStorageKey(oldKey: string, newKey: string): void {
  try {
    const old = localStorage.getItem(oldKey);
    if (old === null) return;
    if (localStorage.getItem(newKey) === null) localStorage.setItem(newKey, old);
    localStorage.removeItem(oldKey);
  } catch {
    // 拿不到存储时只是不记得
  }
}
