import { useState, type ReactNode } from 'react';
import { ArrowLeft, Bookmark, ChevronDown, Download, ExternalLink, FileDiff, History, Maximize2, MoreHorizontal, PanelLeft, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { HUMAN_EDITS_URL } from '../api';
import { FOCUS_RING, STROKE } from '../lib/ui';
import { IconAction } from './VersionHeader';

export interface ExportItem {
  label: string;
  onSelect: () => void;
}

const MENU = 'wb-pop rounded-xl border-0 bg-bg-secondary p-1.5 shadow-pop';
const MENU_ITEM = 'rounded-lg px-2.5 py-2 text-[13px] text-text-secondary focus:bg-bg-hover focus:text-text-primary [&>svg]:text-text-muted';
const MENU_LABEL = 'px-2.5 pb-1 pt-1.5 text-[11px] font-normal tracking-[0.12em] text-text-muted';

/**
 * 顶栏：标题、保存状态、阅读标记、导出主译本、沉浸模式、更多。和页面底色融为一体，不画边框。
 * compact（手机）：导出收进「⋯」，把宽度留给标题。
 */
export function WorkbenchTopBar({ title, original, onShowList, onBack, save, mark, onJump, onClearMark, markBusy,
  onExportPrimary, exportItems, onImmersive, legacyHref, originalUrl, compact = false }: {
  title: string;
  original: string | null;
  onShowList?: () => void;
  onBack: () => void;
  save: ReactNode;
  /** 标记处的文字；null = 没有标记 */
  mark: string | null;
  onJump: () => void;
  onClearMark: () => void;
  markBusy: boolean;
  onExportPrimary: () => void;
  exportItems: ExportItem[];
  /** 进入沉浸模式（整屏只留三栏） */
  onImmersive: () => void;
  legacyHref: string;
  originalUrl: string | null;
  compact?: boolean;
}) {
  const [markOpen, setMarkOpen] = useState(false);
  return (
    <header className="flex items-center gap-2 px-4 pb-3 pt-3.5 md:px-[22px] md:pb-3.5 md:pt-4">
      {onShowList
        ? <IconAction label="显示文章列表" className="-ml-1.5" onClick={onShowList}><PanelLeft aria-hidden className="h-4 w-4" strokeWidth={STROKE} /></IconAction>
        : <IconAction label="回到文章列表" className="-ml-1.5" onClick={onBack}><ArrowLeft aria-hidden className="h-4 w-4" strokeWidth={STROKE} /></IconAction>}
      {/* 桌面上标题的左边缘正好对齐第一栏正文 */}
      <div className="-ml-1 mr-2 min-w-0 flex-1">
        <h1 className="truncate text-[17px] font-semibold leading-snug tracking-[0.01em] text-text-primary [font-family:var(--font-display)] md:text-[19px]"
          title={original ?? title}>{title}</h1>
        {original && <p className="truncate text-[12.5px] italic leading-snug text-text-muted [font-family:var(--font-source)] md:text-[13px]">{original}</p>}
      </div>
      {save}
      {mark !== null && (
        <Popover open={markOpen} onOpenChange={setMarkOpen}>
          <PopoverTrigger asChild>
            <IconAction label="阅读标记" className="text-primary-500 hover:text-primary-600">
              <Bookmark aria-hidden className="h-4 w-4 fill-current" strokeWidth={STROKE} />
            </IconAction>
          </PopoverTrigger>
          <PopoverContent align="end" sideOffset={6} className="wb-pop w-72 rounded-[14px] border-0 p-4 shadow-pop">
            <p className="text-[11px] tracking-[0.12em] text-text-muted">看到这里</p>
            <p className="mt-1.5 line-clamp-3 text-[13.5px] leading-relaxed text-text-primary [font-family:var(--font-display)]">{mark}</p>
            <div className="mt-3.5 flex items-center justify-between">
              <button type="button" aria-label="清除阅读标记" disabled={markBusy} onClick={() => { setMarkOpen(false); onClearMark(); }}
                className={cn('-ml-1.5 inline-flex h-7 items-center gap-1 rounded-full px-2 text-[12px] text-text-muted hover:bg-ink-wash hover:text-text-primary disabled:opacity-40', FOCUS_RING)}>
                <X aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} />清除
              </button>
              <button type="button" onClick={() => { setMarkOpen(false); onJump(); }}
                className={cn('h-7 rounded-full bg-primary-50 px-3.5 text-[12.5px] font-medium text-primary-700 hover:bg-primary-100', FOCUS_RING)}>继续阅读</button>
            </div>
          </PopoverContent>
        </Popover>
      )}
      {!compact && (
        // 不用 overflow-hidden 裁圆角：会把键盘焦点的描边裁掉。两半各自带圆角。
        <div className="ml-1 inline-flex items-stretch rounded-full bg-primary-500 text-[13px] font-medium text-white shadow-plum">
          <button type="button" onClick={onExportPrimary}
            className={cn('inline-flex h-9 items-center gap-1.5 rounded-l-full pl-4 pr-3.5 transition-colors hover:bg-primary-600', FOCUS_RING)}>
            <Download aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} /><span>导出主译本</span>
          </button>
          <span aria-hidden className="my-2 w-px bg-white/30" />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button type="button" aria-label="导出其他版本" title="导出其他版本"
                className={cn('inline-flex items-center rounded-r-full pl-2 pr-2.5 transition-colors hover:bg-primary-600 data-[state=open]:bg-primary-600', FOCUS_RING)}>
                <ChevronDown aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={6} className={cn(MENU, 'w-64')}>
              <DropdownMenuLabel className={MENU_LABEL}>导出 Markdown</DropdownMenuLabel>
              {exportItems.map(item => <DropdownMenuItem key={item.label} className={MENU_ITEM} onSelect={item.onSelect}>{item.label}</DropdownMenuItem>)}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
      <IconAction label="沉浸模式" title="沉浸模式：整屏只留三栏（Esc 退出）" className={compact ? undefined : 'ml-1'} onClick={onImmersive}>
        <Maximize2 aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
      </IconAction>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <IconAction label="更多" className="-mr-1.5"><MoreHorizontal aria-hidden className="h-4 w-4" strokeWidth={STROKE} /></IconAction>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" sideOffset={6} className={cn(MENU, 'w-72')}>
          {compact && (
            <>
              <DropdownMenuItem className={cn(MENU_ITEM, 'font-medium text-primary-700 focus:text-primary-700 [&>svg]:text-primary-500')} onSelect={onExportPrimary}>
                <Download strokeWidth={STROKE} /> 导出主译本
              </DropdownMenuItem>
              <DropdownMenuLabel className={MENU_LABEL}>导出 Markdown</DropdownMenuLabel>
              {exportItems.map(item => <DropdownMenuItem key={item.label} className={cn(MENU_ITEM, 'pl-[34px]')} onSelect={item.onSelect}>{item.label}</DropdownMenuItem>)}
              <DropdownMenuSeparator className="mx-1 my-1.5 bg-border-subtle" />
            </>
          )}
          {originalUrl && (
            <DropdownMenuItem className={MENU_ITEM} asChild>
              <a href={originalUrl} target="_blank" rel="noreferrer"><ExternalLink strokeWidth={STROKE} /> 原文链接</a>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem className={MENU_ITEM} asChild>
            <Link to={legacyHref}><History strokeWidth={STROKE} /> 旧版编辑器（单段重译、质量报告）</Link>
          </DropdownMenuItem>
          <DropdownMenuSeparator className="mx-1 my-1.5 bg-border-subtle" />
          <DropdownMenuItem className={MENU_ITEM} asChild>
            <a href={HUMAN_EDITS_URL}><FileDiff strokeWidth={STROKE} /> 下载全部文章的人工改动</a>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
