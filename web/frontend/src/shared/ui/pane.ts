/** 原文 / 译文「纸」的共用样式（帖子翻译、工具箱文本翻译）：白底、栏头 + 无边框正文 + 底部操作栏，左右两张等高 */
export const PANE = 'flex min-w-0 flex-col overflow-hidden rounded-xl border border-border-subtle bg-white shadow-paper';
export const PANE_HEADER = 'flex h-11 shrink-0 items-center justify-between gap-3 border-b border-border-subtle px-4';
export const PANE_FOOTER = 'flex min-h-12 shrink-0 flex-wrap items-center justify-between gap-2 border-t border-border-subtle bg-bg-tertiary/40 px-3 py-2';
// 高度写在 min-h 上：textarea 带 flex-1（flex-basis 0），单写 h 不生效
export const PANE_TEXTAREA =
  'min-h-[38svh] flex-1 resize-none rounded-none border-0 px-4 py-3 text-[15px] leading-7 focus:border-transparent focus:shadow-none lg:min-h-[max(360px,calc(100svh-300px))]';
