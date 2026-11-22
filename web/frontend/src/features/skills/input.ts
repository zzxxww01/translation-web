import type { ClipboardEvent, DragEvent, KeyboardEvent } from 'react';

/** 触屏设备（手机、平板）：回车留给换行，发送点按钮 */
function touchOnly(): boolean {
  return typeof window !== 'undefined' && Boolean(window.matchMedia?.('(hover: none) and (pointer: coarse)').matches);
}

/**
 * 输入框按键是不是「发送」：电脑上 Enter 发送、Shift+Enter 换行，Ctrl/⌘+Enter 任何设备都发送。
 * 中文输入法选字时的回车（isComposing / keyCode 229）不算。
 */
export function isSendKey(event: KeyboardEvent<HTMLTextAreaElement>): boolean {
  if (event.key !== 'Enter' || event.nativeEvent.isComposing || event.keyCode === 229) return false;
  if (event.metaKey || event.ctrlKey) return true;
  if (event.shiftKey || event.altKey) return false;
  return !touchOnly();
}

export const SEND_HINT = touchOnly() ? '' : 'Enter 发送，Shift + Enter 换行';

export function isImage(name: string): boolean {
  return /\.(png|jpe?g|gif|webp|bmp)$/i.test(name);
}

function stamp(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

/** 截图粘贴进来的文件都叫 image.png：换成带时间的名字，免得一次贴几张互相覆盖、也看不出是哪张 */
function renamePasted(file: File, index: number): File {
  if (file.name && file.name !== 'image.png') return file;
  const ext = (file.type.split('/')[1] || 'png').replace('jpeg', 'jpg');
  return new File([file], `粘贴图片-${stamp()}${index ? `-${index + 1}` : ''}.${ext}`, { type: file.type });
}

/** 粘贴：剪贴板里有文件（截图、复制的图片）就当附件收下；纯文字照常粘贴 */
export function pastedFiles(event: ClipboardEvent<HTMLElement>): File[] {
  const files = Array.from(event.clipboardData?.files ?? []);
  if (!files.length) return [];
  event.preventDefault();
  return files.map(renamePasted);
}

/** 拖文件到输入区 */
export function droppedFiles(event: DragEvent<HTMLElement>): File[] {
  const files = Array.from(event.dataTransfer?.files ?? []);
  if (files.length) event.preventDefault();
  return files;
}
