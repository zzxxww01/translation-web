import type { ReactNode } from 'react';
import {
  BookOpen, Check, ChevronDown, Download, ExternalLink, FileDiff, FileText, Flag, History, Maximize2, Menu,
  MessageCircle, MessageSquare, MoreHorizontal, Newspaper, Sparkles, Wrench, type LucideIcon,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { GlobalTaskIndicator } from '@/components/layout/GlobalTaskIndicator';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { HUMAN_EDITS_URL } from '../api';
import { FOCUS_RING, STROKE } from '../lib/ui';
import { IconAction } from './VersionHeader';

export interface ExportItem {
  label: string;
  icon?: LucideIcon;
  onSelect: () => void;
}

/** 阅读标记：读到全文的百分之几，标记处的文字（悬停看） */
export interface ReadingProgress {
  percent: number;
  text: string;
}

const MENU = 'wb-pop rounded-xl border-0 bg-bg-secondary p-1.5 shadow-pop';
const MENU_ITEM = 'rounded-lg px-2.5 py-2 text-[13px] text-text-secondary focus:bg-bg-hover focus:text-text-primary [&>svg]:text-text-muted';
const MENU_LABEL = 'px-2.5 pb-1 pt-1.5 text-[11px] font-normal tracking-[0.12em] text-text-muted';

// 和 AppLayout 顶部导航同一组功能：工作台里顶部导航收进左上角这个菜单（设计文档 6.1，方案 A）
const FEATURES: { path: string; label: string; icon: LucideIcon }[] = [
  { path: '/articles', label: '文章', icon: Newspaper },
  { path: '/post', label: '帖子翻译', icon: MessageSquare },
  { path: '/wechat', label: '微信排版', icon: FileText },
  { path: '/slack', label: 'Slack 回复', icon: MessageCircle },
  { path: '/tools', label: '工具箱', icon: Wrench },
  { path: '/skills', label: 'Agent', icon: Sparkles },
];

/**
 * 工作台的顶栏，也是整页唯一的一条顶栏（方案 A）：左边功能菜单、品牌、「文章 ›」、标题和英文原标题，
 * 右边保存状态、阅读进度、导出主译本、沉浸模式、更多。
 * 导出：左半边直接下载主译本的 Markdown；▾ 里是主译本的其他去处（PDF、复制全文、公众号格式）和其余各版。
 * compact（手机）：只留功能菜单和标题，导出收进「⋯」。
 */
export function WorkbenchTopBar({ title, original, onShowList, save, mark, onJump, onClearMark, markBusy,
  onExportPrimary, primaryActions, exportItems, exportNotice = null, onImmersive, legacyHref, originalUrl, compact = false }: {
  title: string;
  original: string | null;
  /** 「文章」打开文章列表抽屉；没有就跳回文章页 */
  onShowList?: () => void;
  save: ReactNode;
  /** null = 没有阅读标记 */
  mark: ReadingProgress | null;
  onJump: () => void;
  onClearMark: () => void;
  markBusy: boolean;
  onExportPrimary: () => void;
  /** 主译本的导出方式（Markdown / PDF / 复制全文 / 公众号） */
  primaryActions: ExportItem[];
  /** 其余各版（英文原文、对照版本），下载 Markdown */
  exportItems: ExportItem[];
  /** 复制成功等提示：暂时写在导出按钮上 */
  exportNotice?: string | null;
  /** 进入沉浸模式（整屏只留三栏） */
  onImmersive: () => void;
  legacyHref: string;
  originalUrl: string | null;
  compact?: boolean;
}) {
  const location = useLocation();
  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border-subtle px-3 md:gap-2.5 md:pl-3 md:pr-4">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <IconAction label="功能导航"><Menu aria-hidden className="h-4 w-4" strokeWidth={STROKE} /></IconAction>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" sideOffset={6} className={cn(MENU, 'w-52')}>
          {FEATURES.map(item => (
            <DropdownMenuItem key={item.path} className={cn(MENU_ITEM, item.path === '/articles' && 'font-medium text-primary-700 [&>svg]:text-primary-500')} asChild>
              <Link to={item.path}><item.icon strokeWidth={STROKE} /> {item.label}</Link>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator className="mx-1 my-1.5 bg-border-subtle" />
          <DropdownMenuItem className={MENU_ITEM} asChild>
            <Link to={`/glossary?from=${encodeURIComponent(location.pathname + location.search)}`}><BookOpen strokeWidth={STROKE} /> 术语库</Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {!compact && (
        <>
          <Link to="/articles" aria-label="momo 翻译工作台首页"
            className={cn('flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-md bg-primary-500 text-[14px] leading-none text-white [font-family:var(--font-display)]', FOCUS_RING)}>
            <span aria-hidden>译</span>
          </Link>
          {onShowList
            ? <button type="button" onClick={onShowList} title="文章列表"
                className={cn('shrink-0 rounded-md px-1 text-[13px] text-text-muted transition-colors hover:text-text-primary', FOCUS_RING)}>文章</button>
            : <Link to="/articles" className={cn('shrink-0 rounded-md px-1 text-[13px] text-text-muted hover:text-text-primary', FOCUS_RING)}>文章</Link>}
          <span aria-hidden className="-mx-1 shrink-0 text-[13px] text-text-disabled">›</span>
        </>
      )}
      <h1 className="min-w-0 shrink truncate text-[15.5px] font-semibold leading-snug text-text-primary [font-family:var(--font-display)] md:text-[16px]"
        title={original ?? title}>{title}</h1>
      {original && !compact && (
        <span className="min-w-0 flex-[1_1_0%] truncate text-[13px] italic text-text-muted [font-family:var(--font-source)]">{original}</span>
      )}
      <span className="min-w-0 flex-1" />
      <GlobalTaskIndicator />
      {save}
      {mark && (
        <button type="button" onClick={onJump} disabled={markBusy} title={`回到上次读到的地方：${mark.text.slice(0, 60)}`}
          className={cn('inline-flex h-8 shrink-0 items-center gap-2 rounded-full bg-primary-50 px-3 text-[12.5px] font-medium text-primary-700 transition-colors hover:bg-primary-100 disabled:opacity-60', FOCUS_RING)}>
          <span aria-hidden className="h-1 w-10 overflow-hidden rounded-full bg-primary-200">
            <span className="block h-full rounded-full bg-primary-500" style={{ width: `${mark.percent}%` }} />
          </span>
          读到 {mark.percent}%
        </button>
      )}
      {!compact && (<>
        <span role="status" className="sr-only">{exportNotice ?? ''}</span>
        {/* 不用 overflow-hidden 裁圆角：会把键盘焦点的描边裁掉。两半各自带圆角。 */}
        <div className="inline-flex shrink-0 items-stretch rounded-full bg-primary-500 text-[12.5px] font-medium text-white shadow-plum">
          <button type="button" onClick={onExportPrimary}
            className={cn('inline-flex h-8 items-center gap-1.5 rounded-l-full pl-3.5 pr-3 transition-colors hover:bg-primary-600', FOCUS_RING)}>
            {exportNotice
              ? <><Check aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} /><span>{exportNotice}</span></>
              : <><Download aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} /><span>导出主译本</span></>}
          </button>
          <span aria-hidden className="my-2 w-px bg-white/30" />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button type="button" aria-label="更多导出方式" title="PDF、复制全文、公众号格式、其他版本"
                className={cn('inline-flex items-center rounded-r-full pl-2 pr-2.5 transition-colors hover:bg-primary-600 data-[state=open]:bg-primary-600', FOCUS_RING)}>
                <ChevronDown aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={6} className={cn(MENU, 'w-64')}>
              <ExportMenuItems primaryActions={primaryActions} exportItems={exportItems} />
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </>)}
      <IconAction label="沉浸模式" title="沉浸模式：整屏只留三栏（Esc 退出）" onClick={onImmersive}>
        <Maximize2 aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
      </IconAction>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <IconAction label="更多" className="-mr-1.5"><MoreHorizontal aria-hidden className="h-4 w-4" strokeWidth={STROKE} /></IconAction>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" sideOffset={6} className={cn(MENU, 'w-72')}>
          {compact && (
            <>
              <ExportMenuItems primaryActions={primaryActions} exportItems={exportItems} />
              <DropdownMenuSeparator className="mx-1 my-1.5 bg-border-subtle" />
            </>
          )}
          {mark && (
            <>
              <DropdownMenuItem className={MENU_ITEM} disabled={markBusy} onSelect={onClearMark}>
                <Flag strokeWidth={STROKE} /> 清除阅读标记
              </DropdownMenuItem>
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

/** 导出菜单：主译本的几种去处在上，其余各版的 Markdown 在下 */
function ExportMenuItems({ primaryActions, exportItems }: { primaryActions: ExportItem[]; exportItems: ExportItem[] }) {
  return (
    <>
      <DropdownMenuLabel className={MENU_LABEL}>主译本</DropdownMenuLabel>
      {primaryActions.map(item => (
        <DropdownMenuItem key={item.label} className={MENU_ITEM} onSelect={item.onSelect}>
          {item.icon && <item.icon strokeWidth={STROKE} />} {item.label}
        </DropdownMenuItem>
      ))}
      <DropdownMenuSeparator className="mx-1 my-1.5 bg-border-subtle" />
      <DropdownMenuLabel className={MENU_LABEL}>其他版本 · Markdown</DropdownMenuLabel>
      {exportItems.map(item => <DropdownMenuItem key={item.label} className={cn(MENU_ITEM, 'pl-[34px]')} onSelect={item.onSelect}>{item.label}</DropdownMenuItem>)}
    </>
  );
}
