import { Clapperboard, FileText, MessageCircle, Mic, Sparkles, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

// agents.json 里 icon 字段的取值；没登记的统一用 Sparkles
const ICONS: Record<string, LucideIcon> = {
  chat: MessageCircle,
  article: FileText,
  video: Clapperboard,
  podcast: Mic,
};

export function AgentIcon({ icon, className }: { icon: string; className?: string }) {
  const Icon = ICONS[icon] ?? Sparkles;
  return <Icon aria-hidden className={cn('h-4 w-4 shrink-0', className)} />;
}
