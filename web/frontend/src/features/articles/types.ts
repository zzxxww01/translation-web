/** 一路翻译（主项目或孪生项目）在后台的运行状态，来自 translation-status。 */
export interface TrackStatus {
  active: boolean;
  run_id: string | null;
  status: string | null;
  current_step: string | null;
  translated: number | null;
  total: number | null;
  error: string | null;
}

export interface WorkbenchProject {
  id: string;
  title: string;
  title_translation: string | null;
  original_url: string | null;
  created_at: string;
  claude_run_id: string | null;
  progress: { total: number; approved: number };
  status: TrackStatus;
}

export interface ClaudeImportRecord {
  run_id: string | null;
  aligned: number;
  unaligned: number;
  merged_blocks: number;
  imported_at: string;
}

/** 译本 2：同源孪生项目。kind=model 是换模型再翻，kind=claude 是从 Claude 任务导入。 */
export interface WorkbenchVariant {
  id: string;
  kind: 'model' | 'claude';
  label: string;
  title_translation: string | null;
  progress: { total: number; approved: number };
  status: TrackStatus;
  import: ClaudeImportRecord | null;
}

export interface WorkbenchRow {
  /** "section:<章节 id>" 或 "<章节 id>/<段落 id>" */
  key: string;
  /** section（章节标题）或段落的 element_type：p / h1–h4 / li / blockquote / code / table / image */
  kind: string;
  section_id: string;
  paragraph_id: string | null;
  heading_level?: number | null;
  is_metadata?: boolean;
  source: string;
  image?: string | null;
  /** 译本 1（网页版主项目） */
  web: string | null;
  /** 各个译本 2，键是孪生项目 id */
  alt: Record<string, string | null>;
}

export interface Workbench {
  project: WorkbenchProject;
  variants: WorkbenchVariant[];
  rows: WorkbenchRow[];
}

export type PaneId = 'source' | 'web' | 'alt';

export type DiffSegment = { op: 'equal' | 'insert' | 'delete'; text: string };

/** 人工改过的一段：机翻初稿（没有就是 null，人写的）→ 现在的译文 */
export interface HumanChange {
  key: string;
  section_id: string;
  section_title: string;
  paragraph_id: string;
  kind: string;
  source: string;
  before: string | null;
  after: string;
  segments: DiffSegment[];
}

export interface ChangesReport {
  total: number;
  changed: number;
  changes: HumanChange[];
}
