import payload from '../../../../config/editing_options.json';

export const EDITING_OPTION_VERSION = payload.version;
export const EDITING_OPTIONS = payload.options;
export const EDITING_OPTIONS_BY_ID = Object.fromEntries(EDITING_OPTIONS.map(item => [item.id, item]));
export function getEditingInstruction(id: string): string {
  return EDITING_OPTIONS_BY_ID[id]?.instruction ?? '';
}
