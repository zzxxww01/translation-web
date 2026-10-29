import type { Harness } from '@/features/skills/harness';

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
  /** 用户选的主译本（主项目或孪生项目 id）；null = 没选过 */
  primary_target?: string | null;
  /** 实际的主译本：选过的那个，或后端按默认规则算出的（services/article_primary.py） */
  primary?: string;
  progress: { total: number; approved: number };
  status: TrackStatus;
}

export interface ClaudeImportRecord {
  run_id: string | null;
  /** 跑这一版的 Agent；旧记录没有，用 label 反推 */
  agent?: Harness;
  model?: string | null;
  aligned: number;
  unaligned: number;
  merged_blocks: number;
  imported_at: string;
}

/** 网页版以外的一版：同源孪生项目。kind=model 是以前换模型再翻的，kind=claude 是从 Agent 任务导入的。 */
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
  /** 同一个自然段被导入器拆开后的共同标识。 */
  block?: string | null;
  heading_level?: number | null;
  is_metadata?: boolean;
  source: string;
  image?: string | null;
  /** 网页版（主项目）的译文 */
  web: string | null;
  /** 其余各版的译文，键是孪生项目 id */
  alt: Record<string, string | null>;
}

export interface Workbench {
  project: WorkbenchProject;
  variants: WorkbenchVariant[];
  rows: WorkbenchRow[];
  reading_mark?: { key: string; at: string } | null;
}

export type PaneId = 'source' | 'main' | 'compare';

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
