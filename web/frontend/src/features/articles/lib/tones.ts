import type { Tone } from './versions';

/** 状态圆点的颜色：栏头状态行、对照栏标签、收起的竖条共用 */
export const TONE_DOT: Record<Tone, string> = {
  done: 'bg-success',
  busy: 'bg-info shadow-[0_0_0_3px_var(--color-info-light)]',
  wait: 'bg-warning',
  error: 'bg-error',
  idle: 'bg-border',
};
