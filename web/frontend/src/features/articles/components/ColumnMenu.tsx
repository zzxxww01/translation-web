import { useState } from 'react';
import { MoreHorizontal } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { FOCUS_RING, STROKE } from '../lib/ui';
import { IconAction } from './VersionHeader';

export interface MenuItem {
  label: string;
  onSelect: () => void;
}

/** 栏头的「⋯」：这一栏自己的操作 */
export function ColumnMenu({ label, items }: { label: string; items: MenuItem[] }) {
  const [open, setOpen] = useState(false);
  if (!items.length) return null;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <IconAction label={label} className="data-[state=open]:bg-ink-wash data-[state=open]:text-text-primary">
          <MoreHorizontal aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
        </IconAction>
      </PopoverTrigger>
      <PopoverContent align="end" sideOffset={6} className="wb-pop w-52 rounded-xl border-0 p-1.5 shadow-pop">
        {items.map(item => (
          <button key={item.label} type="button" onClick={() => { setOpen(false); item.onSelect(); }}
            className={cn('block w-full rounded-lg px-2.5 py-2 text-left text-[13px] text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary', FOCUS_RING, 'focus-visible:-outline-offset-2')}>
            {item.label}
          </button>
        ))}
      </PopoverContent>
    </Popover>
  );
}
