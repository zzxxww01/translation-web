import type { TranslationVersion } from '@/shared/types';


export function getOptimizationHistory(
  versions: TranslationVersion[],
  baseVersionId: string,
  limit = 3
): Array<{ role: 'user'; content: string }> {
  const byId = new Map(versions.map(version => [version.id, version]));
  const baseVersion = byId.get(baseVersionId);
  if (!baseVersion || limit <= 0) {
    return [];
  }

  const lineage: TranslationVersion[] = [];
  const visited = new Set<string>();
  let current: TranslationVersion | undefined = baseVersion;

  while (current && !visited.has(current.id)) {
    visited.add(current.id);
    if (
      current.sourceRevision === baseVersion.sourceRevision &&
      current.sourceText === baseVersion.sourceText
    ) {
      lineage.push(current);
    }
    current = current.parentVersionId
      ? byId.get(current.parentVersionId)
      : undefined;
  }

  return lineage
    .reverse()
    .filter(version => Boolean(version.instruction?.trim()))
    .slice(-limit)
    .map(version => ({
      role: 'user' as const,
      content: version.instruction!.trim(),
    }));
}
