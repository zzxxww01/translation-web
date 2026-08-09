import { ParagraphStatus } from '@/shared/constants';
import type { Paragraph, Project, Section } from '@/shared/types';

export type ParagraphFilter =
  | 'all'
  | 'untranslated'
  | 'unconfirmed'
  | 'modified'
  | 'error';

export function isParagraphConfirmed(paragraph: Paragraph): boolean {
  return paragraph.status === ParagraphStatus.APPROVED || Boolean(paragraph.confirmed);
}

export function isParagraphUntranslated(paragraph: Paragraph): boolean {
  return (
    !paragraph.translation?.trim() ||
    paragraph.status === ParagraphStatus.PENDING ||
    paragraph.status === ParagraphStatus.TRANSLATING
  );
}

export function isParagraphUnresolved(
  paragraph: Paragraph,
  isDirty = false,
  hasError = false
): boolean {
  return !isParagraphConfirmed(paragraph) || isDirty || hasError;
}

export function matchesParagraphFilter(
  filter: ParagraphFilter,
  paragraph: Paragraph,
  options: { isDirty?: boolean; hasError?: boolean; search?: string; draft?: string } = {}
): boolean {
  const { isDirty = false, hasError = false, search = '', draft = '' } = options;
  const query = search.trim().toLocaleLowerCase();
  const matchesSearch =
    !query ||
    paragraph.source.toLocaleLowerCase().includes(query) ||
    draft.toLocaleLowerCase().includes(query);

  if (!matchesSearch) return false;
  if (filter === 'all') return true;
  if (filter === 'untranslated') return isParagraphUntranslated(paragraph);
  if (filter === 'unconfirmed') return !isParagraphConfirmed(paragraph);
  if (filter === 'modified') {
    return paragraph.status === ParagraphStatus.MODIFIED || isDirty;
  }
  return hasError;
}

export function findFirstUnresolvedParagraphId(paragraphs: Paragraph[]): string | null {
  return paragraphs.find(paragraph => isParagraphUnresolved(paragraph))?.id ?? paragraphs[0]?.id ?? null;
}

export function findResumeSectionId(sections: Section[]): string | null {
  const incomplete = sections.find(
    section => !section.is_complete || section.approved_count < section.total_paragraphs
  );
  return incomplete?.section_id ?? sections[0]?.section_id ?? null;
}

export function sortProjectsByRecency(projects: Project[]): Project[] {
  return [...projects].sort((left, right) => {
    const rightTime = right.created_at ? Date.parse(right.created_at) : 0;
    const leftTime = left.created_at ? Date.parse(left.created_at) : 0;
    return rightTime - leftTime;
  });
}
