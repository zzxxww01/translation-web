import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import type { VersionView } from '../lib/versions';
import { TONE_DOT } from '../lib/tones';

/** 窄于 width 时返回 true（jsdom 没有 ResizeObserver，一律当宽屏） */
function useNarrow(width: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(([entry]) => setNarrow(entry.contentRect.width < width));
    observer.observe(el);
    return () => observer.disconnect();
  }, [width]);
  return [ref, narrow] as const;
}

const dot = (version: VersionView) => version.tone !== 'done' && version.tone !== 'idle'
  ? <span aria-hidden className={cn('h-1.5 w-1.5 shrink-0 rounded-full', TONE_DOT[version.tone])} /> : null;

/** 对照栏：分段胶囊标签（宽）或下拉（窄、手机）。add 是末尾的「＋」。 */
export function VersionTabs({ versions, value, onChange, add, forceMenu = false }: {
  versions: VersionView[];
  value: string;
  onChange: (id: string) => void;
  add?: ReactNode;
  forceMenu?: boolean;
}) {
  const [ref, narrow] = useNarrow(420);
  const [open, setOpen] = useState(false);
  const current = versions.find(version => version.id === value) ?? versions[0];
  if (forceMenu || narrow) {
    return (
      <div ref={ref} className="flex items-center gap-1">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button type="button" aria-label="切换对照版本"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#f5eff1] px-3 py-1 text-[12.5px] font-medium text-text-primary">
              {dot(current)}{current.name}<ChevronDown className="h-3.5 w-3.5 text-text-muted" />
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-56 rounded-xl p-1.5">
            {versions.map(version => (
              <button key={version.id} type="button" onClick={() => { setOpen(false); onChange(version.id); }}
                className={cn('flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-[13px] hover:bg-bg-hover', version.id === value && 'bg-primary-50')}>
                {dot(version)}<span className="flex-1">{version.name}</span>
                {version.model && <span className="truncate text-[11px] text-text-muted">{version.model}</span>}
              </button>
            ))}
          </PopoverContent>
        </Popover>
        {add}
      </div>
    );
  }
  return (
    <div ref={ref} role="tablist" aria-label="对照版本" className="inline-flex max-w-full items-center gap-0.5 rounded-full bg-[#f5eff1] p-[3px]">
      {versions.map(version => (
        <button key={version.id} type="button" role="tab" aria-selected={version.id === value} onClick={() => onChange(version.id)}
          className={cn('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-[12.5px] transition-colors',
            version.id === value
              ? 'bg-white font-medium text-text-primary shadow-[0_1px_2px_rgba(43,39,48,0.08),0_1px_6px_rgba(43,39,48,0.05)]'
              : 'text-text-muted hover:text-text-primary')}>
          {dot(version)}{version.name}
        </button>
      ))}
      {add}
    </div>
  );
}
