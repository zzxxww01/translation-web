import { useState, type ReactNode } from 'react';
import { ArrowLeft, Bookmark, ChevronDown, Download, ExternalLink, FileDiff, MoreHorizontal, PanelLeft, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { HUMAN_EDITS_URL } from '../api';
import { IconAction } from './VersionHeader';

export interface ExportItem {
  label: string;
  onSelect: () => void;
}

/** 顶栏：标题、保存状态、阅读标记、导出主译本、更多。和页面底色融为一体，不画边框。 */
export function WorkbenchTopBar({ title, original, onShowList, onBack, save, mark, onJump, onClearMark, markBusy,
  onExportPrimary, exportItems, legacyHref, originalUrl }: {
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
  legacyHref: string;
  originalUrl: string | null;
}) {
  const [markOpen, setMarkOpen] = useState(false);
  return (
    <header className="flex items-center gap-3 px-4 pb-3.5 pt-4 md:px-[26px]">
      {onShowList
        ? <IconAction label="显示文章列表" onClick={onShowList}><PanelLeft className="h-4 w-4" /></IconAction>
        : <IconAction label="回到文章列表" onClick={onBack}><ArrowLeft className="h-4 w-4" /></IconAction>}
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-[19px] font-semibold leading-snug tracking-[0.01em] text-text-primary [font-family:var(--font-display)]" title={original ?? title}>{title}</h1>
        {original && <p className="truncate text-[13px] italic text-text-muted [font-family:var(--font-source)]">{original}</p>}
      </div>
      {save}
      {mark !== null && (
        <Popover open={markOpen} onOpenChange={setMarkOpen}>
          <PopoverTrigger asChild>
            <IconAction label="阅读标记" className="text-primary-500"><Bookmark className="h-4 w-4 fill-current" /></IconAction>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-72 rounded-xl p-3">
            <p className="text-[11px] tracking-[0.12em] text-text-muted">看到这里</p>
            <p className="mt-1 line-clamp-3 text-[13px] leading-relaxed text-text-primary [font-family:var(--font-display)]">{mark}</p>
            <div className="mt-3 flex items-center justify-between">
              <button type="button" aria-label="清除阅读标记" disabled={markBusy} onClick={() => { setMarkOpen(false); onClearMark(); }}
                className="inline-flex items-center gap-1 text-[12px] text-text-muted hover:text-text-primary disabled:opacity-40">
                <X className="h-3.5 w-3.5" />清除
              </button>
              <button type="button" onClick={() => { setMarkOpen(false); onJump(); }}
                className="rounded-full bg-primary-50 px-3 py-1 text-[12.5px] text-primary-700 hover:bg-primary-100">继续阅读</button>
            </div>
          </PopoverContent>
        </Popover>
      )}
      <div className="inline-flex items-stretch overflow-hidden rounded-full bg-primary-500 text-[13px] font-medium text-white shadow-[0_1px_2px_rgba(116,42,79,0.25),0_4px_12px_rgba(163,61,112,0.18)]">
        <button type="button" onClick={onExportPrimary} className="inline-flex items-center gap-1.5 py-2 pl-4 pr-3.5 hover:bg-primary-600">
          <Download className="h-3.5 w-3.5" /><span className="hidden sm:inline">导出主译本</span>
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" aria-label="导出其他版本" className="border-l border-white/30 px-2.5 hover:bg-primary-600"><ChevronDown className="h-3.5 w-3.5" /></button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {exportItems.map(item => <DropdownMenuItem key={item.label} onSelect={item.onSelect}>{item.label}</DropdownMenuItem>)}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <IconAction label="更多"><MoreHorizontal className="h-4 w-4" /></IconAction>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          {originalUrl && (
            <DropdownMenuItem asChild>
              <a href={originalUrl} target="_blank" rel="noreferrer"><ExternalLink className="h-4 w-4" /> 原文链接</a>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem asChild><Link to={legacyHref}>旧版编辑器（单段重译、质量报告）</Link></DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild><a href={HUMAN_EDITS_URL}><FileDiff className="h-4 w-4" /> 下载全部文章的人工改动</a></DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
