import type { AddTermRequest } from '@/features/confirmation/api/glossaryApi';
import type { GlossaryTerm, TranslationStrategy } from '@/features/confirmation/types';

export interface EffectiveGlossaryTerm extends GlossaryTerm {
  /** 实际生效的那一份。后端 2026-08-09 起全局优先，所以同名时恒为 global。 */
  effectiveScope: 'global' | 'project';
  /** 同名项目条目存在但被全局压掉、事实上不生效时给出，用于在表格里打灰标。 */
  shadowedProjectTerm?: GlossaryTerm;
}

export interface GlossaryMutationResult {
  terms: GlossaryTerm[];
  originals: string[];
}

const strategies = new Set<TranslationStrategy>([
  'translate',
  'first_annotate',
  'preserve',
  'preserve_annotate',
]);

function keyFor(original: string): string {
  return original.trim().toLocaleLowerCase();
}

/**
 * 合成「有效术语」，顺序必须与后端 `GlossaryManager.merge`
 * （src/core/glossary.py:237-266）一致：**先项目、后全局，全局覆盖同名项目条目**。
 *
 * 此前这里是反的（先全局、项目覆盖），于是同一个词在界面上显示的是项目译法、
 * 实际翻译时用的却是全局译法——用户按界面改词却改不动结果。项目词表的正当用途
 * 是补充全局没有的词，不是覆盖全局。
 */
export function buildEffectiveTerms(
  globalTerms: GlossaryTerm[],
  projectTerms: GlossaryTerm[]
): EffectiveGlossaryTerm[] {
  const terms = new Map<string, EffectiveGlossaryTerm>();

  projectTerms.forEach(term => {
    terms.set(keyFor(term.original), {
      ...term,
      scope: 'project',
      effectiveScope: 'project',
    });
  });

  globalTerms.forEach(term => {
    const key = keyFor(term.original);
    const shadowed = terms.get(key);
    terms.set(key, {
      ...term,
      scope: 'global',
      effectiveScope: 'global',
      // 只有真的存在同名项目条目时才记，用于提示"这条项目术语不生效"
      shadowedProjectTerm:
        shadowed?.effectiveScope === 'project' ? shadowed : undefined,
    });
  });

  return Array.from(terms.values());
}

export function upsertGlossaryTerm(
  terms: GlossaryTerm[],
  nextTerm: GlossaryTerm
): GlossaryTerm[] {
  const nextKey = keyFor(nextTerm.original);
  const found = terms.some(term => keyFor(term.original) === nextKey);
  if (!found) return [nextTerm, ...terms];
  return terms.map(term => (keyFor(term.original) === nextKey ? nextTerm : term));
}

export function removeGlossaryTerms(
  terms: GlossaryTerm[],
  originals: string[]
): GlossaryTerm[] {
  const removed = new Set(originals.map(keyFor));
  return terms.filter(term => !removed.has(keyFor(term.original)));
}

export function applyGlossaryMutation(
  terms: GlossaryTerm[],
  action: string,
  result: GlossaryMutationResult
): GlossaryTerm[] {
  if (action === 'delete') return removeGlossaryTerms(terms, result.originals);
  return result.terms.reduce(upsertGlossaryTerm, terms);
}

function normalizeImportedTerm(value: unknown): AddTermRequest | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  const original = typeof item.original === 'string' ? item.original.trim() : '';
  if (!original) return null;

  const strategy = strategies.has(item.strategy as TranslationStrategy)
    ? (item.strategy as TranslationStrategy)
    : 'translate';
  const tags = Array.isArray(item.tags)
    ? item.tags.filter((tag): tag is string => typeof tag === 'string' && Boolean(tag.trim()))
    : [];

  return {
    original,
    translation:
      typeof item.translation === 'string' ? item.translation.trim() || null : null,
    strategy,
    note: typeof item.note === 'string' ? item.note.trim() || null : null,
    tags,
    status: item.status === 'disabled' ? 'disabled' : 'active',
  };
}

export function parseGlossaryImport(raw: string): AddTermRequest[] {
  const parsed = JSON.parse(raw) as unknown;
  const values = Array.isArray(parsed)
    ? parsed
    : parsed && typeof parsed === 'object' && Array.isArray((parsed as { terms?: unknown }).terms)
      ? (parsed as { terms: unknown[] }).terms
      : [];

  const seen = new Set<string>();
  return values.reduce<AddTermRequest[]>((result, value) => {
    const term = normalizeImportedTerm(value);
    if (!term) return result;
    const key = keyFor(term.original);
    if (seen.has(key)) return result;
    seen.add(key);
    result.push(term);
    return result;
  }, []);
}
