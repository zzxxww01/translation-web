import type { AddTermRequest } from '@/features/confirmation/api/glossaryApi';
import type { GlossaryTerm, TranslationStrategy } from '@/features/confirmation/types';

export interface EffectiveGlossaryTerm extends GlossaryTerm {
  effectiveScope: 'global' | 'project';
  overridesGlobal: boolean;
  globalTerm?: GlossaryTerm;
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

export function buildEffectiveTerms(
  globalTerms: GlossaryTerm[],
  projectTerms: GlossaryTerm[]
): EffectiveGlossaryTerm[] {
  const terms = new Map<string, EffectiveGlossaryTerm>();

  globalTerms.forEach(term => {
    terms.set(keyFor(term.original), {
      ...term,
      scope: 'global',
      effectiveScope: 'global',
      overridesGlobal: false,
    });
  });

  projectTerms.forEach(term => {
    const globalTerm = terms.get(keyFor(term.original));
    terms.set(keyFor(term.original), {
      ...term,
      scope: 'project',
      effectiveScope: 'project',
      overridesGlobal: Boolean(globalTerm),
      globalTerm,
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
