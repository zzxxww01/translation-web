import { useState } from 'react';
import { MoreHorizontal } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
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
        <IconAction label={label}><MoreHorizontal className="h-4 w-4" /></IconAction>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-48 rounded-xl border-border-subtle p-1.5 shadow-[0_12px_32px_rgba(43,39,48,0.14)]">
        {items.map(item => (
          <button key={item.label} type="button" onClick={() => { setOpen(false); item.onSelect(); }}
            className="block w-full rounded-md px-2.5 py-1.5 text-left text-[13px] text-text-secondary hover:bg-bg-hover hover:text-text-primary">
            {item.label}
          </button>
        ))}
      </PopoverContent>
    </Popover>
  );
}
