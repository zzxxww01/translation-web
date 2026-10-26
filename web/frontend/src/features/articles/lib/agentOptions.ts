import { HARNESSES } from '@/features/skills/harness';

// All article entry points use the supported tools, with the translation default first.
export const ARTICLE_HARNESSES = [...HARNESSES].sort(
  (a, b) => Number(b.id === 'codex') - Number(a.id === 'codex'),
);
