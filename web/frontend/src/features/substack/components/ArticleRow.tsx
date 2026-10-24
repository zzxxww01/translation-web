import type { ReactNode } from 'react';
import { BellRing, CheckCircle2, Download, ExternalLink, FolderOpen, Languages, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import type { SubstackArticle } from '../api';

export type ImportMode = 'import' | 'translate';

interface ArticleRowProps {
  article: SubstackArticle;
  busyMode?: ImportMode;
  /** 上次打开文章库之后才发布的文章 */
  isNew?: boolean;
  /** 没导入的文章：导入，或导入后马上翻译 */
  onImport: (article: SubstackArticle, mode: ImportMode) => void;
  /** 已导入的文章：开始（或继续）翻译 */
  onTranslate: (article: SubstackArticle) => void;
  onOpen: (projectId: string) => void;
}

const dateFormatter = new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });

function formatPostDate(value: string): string {
  const time = Date.parse(value);
  return Number.isFinite(time) ? dateFormatter.format(time) : '';
}

/** 仿 Substack 归档页的一行：日期 · 付费 · 字数 / 英文标题 / 中文标题和摘要 / 副标题 + 右侧封面。 */
export function ArticleRow({ article, busyMode, isNew, onImport, onTranslate, onOpen }: ArticleRowProps) {
  const projectId = article.project_id;
  const titleClass = 'text-base font-semibold leading-snug text-text-primary hover:text-primary-700';

  const openButton = projectId && (
    <Button
      type="button"
      size="sm"
      variant="outline"
      leftIcon={<FolderOpen className="h-3.5 w-3.5" />}
      onClick={() => onOpen(projectId)}
    >
      打开项目
    </Button>
  );
  const translateButton = (label: string) => (
    <Button
      type="button"
      size="sm"
      leftIcon={<Languages className="h-3.5 w-3.5" />}
      onClick={() => onTranslate(article)}
    >
      {label}
    </Button>
  );

  let actions: ReactNode;
  if (busyMode) {
    actions = (
      <span className="inline-flex items-center gap-1.5 text-sm text-text-muted">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        {busyMode === 'import' ? '正在下载并导入…' : projectId ? '正在开始翻译…' : '正在导入，随后开始翻译…'}
      </span>
    );
  } else if (!projectId || article.status === 'not_imported') {
    actions = (
      <>
        <Button
          type="button"
          size="sm"
          variant="outline"
          leftIcon={<Download className="h-3.5 w-3.5" />}
          onClick={() => onImport(article, 'import')}
        >
          导入
        </Button>
        <Button
          type="button"
          size="sm"
          leftIcon={<Languages className="h-3.5 w-3.5" />}
          onClick={() => onImport(article, 'translate')}
        >
          导入并翻译
        </Button>
      </>
    );
  } else if (article.status === 'awaiting_terms') {
    actions = (
      <>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="border-warning bg-warning-light text-warning hover:border-warning hover:bg-warning hover:text-white"
          leftIcon={<BellRing className="h-3.5 w-3.5" />}
          onClick={() => onOpen(projectId)}
        >
          等你确认术语
        </Button>
        <span className="text-xs text-text-muted">10 分钟内不确认，会自动按建议继续翻译</span>
      </>
    );
  } else if (article.status === 'translating') {
    actions = (
      <>
        <span className="inline-flex items-center gap-1.5 text-sm text-primary-700">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          翻译中 {article.progress}%
        </span>
        {openButton}
      </>
    );
  } else if (article.status === 'translated') {
    actions = (
      <>
        <span className="inline-flex items-center gap-1 text-sm font-medium text-success">
          <CheckCircle2 className="h-3.5 w-3.5" />
          已译完
        </span>
        {openButton}
      </>
    );
  } else if (article.status === 'partial') {
    actions = (
      <>
        <span className="text-sm text-text-muted">已翻 {article.progress}%，没翻完</span>
        {openButton}
        {translateButton('继续翻译')}
      </>
    );
  } else {
    actions = (
      <>
        <span className="text-sm text-text-muted">已导入，还没翻译</span>
        {openButton}
        {translateButton('开始翻译')}
      </>
    );
  }

  return (
    <li className="flex gap-4 border-b border-border py-5 last:border-b-0">
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-muted">
          <span>{formatPostDate(article.post_date)}</span>
          {article.is_paid && (
            <span className="rounded bg-primary-50 px-1.5 py-0.5 font-medium text-primary-700">付费</span>
          )}
          {article.wordcount ? <span>{article.wordcount.toLocaleString('en-US')} 词</span> : null}
          {isNew && <span className="rounded bg-success-light px-1.5 py-0.5 font-medium text-success">新</span>}
        </div>

        {projectId ? (
          // 已导入的文章，点标题直接进项目；原文从旁边的小图标去
          <div className="flex items-start gap-1.5">
            <button type="button" className={`text-left ${titleClass}`} onClick={() => onOpen(projectId)}>
              {article.title}
            </button>
            <a
              href={article.url}
              target="_blank"
              rel="noreferrer"
              title="在 Substack 打开原文"
              aria-label="在 Substack 打开原文"
              className="mt-1 shrink-0 text-text-muted hover:text-primary-700"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        ) : (
          <a
            href={article.url}
            target="_blank"
            rel="noreferrer"
            className={`group inline-flex items-start gap-1 ${titleClass}`}
          >
            <span>{article.title}</span>
            <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-60" />
          </a>
        )}

        {article.zh_title && <p className="text-[15px] font-medium leading-snug text-text-primary">{article.zh_title}</p>}
        {article.zh_summary && <p className="line-clamp-2 text-sm text-text-secondary">{article.zh_summary}</p>}
        {article.subtitle && <p className="line-clamp-1 text-xs text-text-muted">{article.subtitle}</p>}

        <div className="flex flex-wrap items-center gap-2 pt-1.5">{actions}</div>
      </div>

      {article.cover_image && (
        <img
          src={article.cover_image}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          className="hidden h-20 w-32 shrink-0 rounded-md border border-border object-cover sm:block"
        />
      )}
    </li>
  );
}
