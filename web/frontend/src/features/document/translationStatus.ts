import type { TranslationStatus } from '../confirmation/types';


export function isTranslationRunActive(
  status: TranslationStatus | null | undefined,
  projectId: string | undefined
): boolean {
  if (!status || !projectId || status.active_project_id !== projectId) {
    return false;
  }
  return (
    status.status === 'starting' ||
    status.status === 'processing' ||
    Boolean(status.is_cancelling)
  );
}
