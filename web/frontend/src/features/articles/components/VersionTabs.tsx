import { useLayoutEffect, useRef, useState, type ComponentProps, type ReactNode } from 'react';
import { flushSync } from 'react-dom';
import * as Menu from '@radix-ui/react-dropdown-menu';
import { Check, ChevronDown, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { VersionView } from '../lib/versions';
import { TONE_DOT } from '../lib/tones';
import { FOCUS_RING, onTabKeys, STROKE } from '../lib/ui';

/** 对照栏宽度不足这么多时，分段标签收成下拉（设计文档 6.2） */
const NARROW_COLUMN = 420;

/**
 * 量的是整栏（PaneGrid 栏头格子上的 data-pane），不是标签本身占的位置。
 * ResizeObserver 在绘制前回调，用 flushSync 当帧换掉，不会先闪一下标签。jsdom 没有 ResizeObserver，一律当宽屏。
 */
function useNarrowColumn() {
  const ref = useRef<HTMLDivElement>(null);
  const [narrow, setNarrow] = useState(false);
  useLayoutEffect(() => {
    const column = ref.current?.closest<HTMLElement>('[data-pane]');
    if (!column || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(([entry]) => {
      const width = entry.borderBoxSize?.[0]?.inlineSize ?? entry.contentRect.width;
      if (width > 0) flushSync(() => setNarrow(width < NARROW_COLUMN));
    });
    observer.observe(column);
    return () => observer.disconnect();
  }, []);
  return [ref, narrow] as const;
}

const dot = (version: VersionView) => version.tone !== 'done' && version.tone !== 'idle'
  ? <span aria-hidden className={cn('h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[version.tone])} /> : null;

/** 分段标签末尾的「＋」：不是标签，放在 tablist 外面（视觉上仍在同一条胶囊里） */
export function AddVersionButton({ className, ...props }: ComponentProps<'button'>) {
  return (
    <button type="button" aria-label="用 Agent 再翻一版" title="用 Agent 再翻一版"
      className={cn('inline-flex h-[26px] w-[30px] shrink-0 items-center justify-center rounded-full text-primary-700 transition-colors hover:bg-bg-secondary hover:shadow-thumb', FOCUS_RING, className)}
      {...props}>
      <Plus aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} />
    </button>
  );
}

/** 对照栏：分段胶囊标签（宽）或下拉（窄、手机）。add 是末尾的「＋」（AddVersionButton 套上弹框）。 */
export function VersionTabs({ versions, value, onChange, add, forceMenu = false, controls }: {
  versions: VersionView[];
  value: string;
  onChange: (id: string) => void;
  add?: ReactNode;
  forceMenu?: boolean;
  /** 标签控制的那一栏正文的 id */
  controls?: string;
}) {
  const [ref, narrow] = useNarrowColumn();
  const current = versions.find(version => version.id === value) ?? versions[0];
  if (forceMenu || narrow) {
    return (
      <div ref={ref} className="flex min-w-0 items-center gap-1 rounded-full bg-bg-inset p-[3px]">
        <Menu.Root>
          <Menu.Trigger asChild>
            <button type="button" aria-label={`对照版本：${current.name}`}
              className={cn('inline-flex h-[26px] min-w-0 items-center gap-1.5 rounded-full bg-bg-secondary pl-3 pr-2 text-[12.5px] font-medium text-text-primary shadow-thumb', FOCUS_RING)}>
              {dot(current)}<span className="truncate">{current.name}</span>
              <ChevronDown aria-hidden className="h-3.5 w-3.5 shrink-0 text-text-muted" strokeWidth={STROKE} />
            </button>
          </Menu.Trigger>
          <Menu.Portal>
            <Menu.Content align="start" sideOffset={6}
              className="wb-pop z-50 w-60 rounded-xl bg-bg-secondary p-1.5 shadow-pop">
              <Menu.Label className="px-2.5 pb-1 pt-1.5 text-[11px] tracking-[0.12em] text-text-muted">对照版本</Menu.Label>
              <Menu.RadioGroup value={current.id} onValueChange={onChange}>
                {versions.map(version => (
                  <Menu.RadioItem key={version.id} value={version.id}
                    className="flex cursor-default select-none items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] text-text-primary outline-none data-[highlighted]:bg-bg-hover">
                    {dot(version) ?? <span aria-hidden className="h-1.5 w-1.5 shrink-0" />}
                    <span className="min-w-0 flex-1 truncate">{version.name}</span>
                    {version.model && <span className="max-w-[45%] shrink-0 truncate text-[11px] text-text-muted">{version.model}</span>}
                    <span className="flex w-3.5 shrink-0 justify-center text-primary-500">
                      <Menu.ItemIndicator><Check aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} /></Menu.ItemIndicator>
                    </span>
                  </Menu.RadioItem>
                ))}
              </Menu.RadioGroup>
            </Menu.Content>
          </Menu.Portal>
        </Menu.Root>
        {add}
      </div>
    );
  }
  const ids = versions.map(version => version.id);
  return (
    <div ref={ref} className="inline-flex max-w-full min-w-0 items-center gap-0.5 rounded-full bg-bg-inset p-[3px]">
      <div role="tablist" aria-label="对照版本" className="flex min-w-0 items-center gap-0.5">
        {versions.map(version => {
          const selected = version.id === current.id;
          return (
            <button key={version.id} type="button" role="tab" data-tab-id={version.id} aria-selected={selected}
              aria-controls={controls} tabIndex={selected ? 0 : -1}
              onClick={() => onChange(version.id)} onKeyDown={event => onTabKeys(event, ids, current.id, onChange)}
              className={cn('inline-flex h-[26px] items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-[12.5px]', FOCUS_RING,
                selected ? 'bg-bg-secondary font-medium text-text-primary shadow-thumb' : 'text-text-muted hover:text-text-primary')}>
              {dot(version)}{version.name}
            </button>
          );
        })}
      </div>
      {add}
    </div>
  );
}
