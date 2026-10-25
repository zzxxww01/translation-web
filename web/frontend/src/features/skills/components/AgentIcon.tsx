import { Captions, Languages, Podcast, Sparkles, Wand2, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

// agents.json 里 icon 字段的取值（旧名也认）；没登记的用 Wand2
const ICONS: Record<string, { icon: LucideIcon; color: string }> = {
  general: { icon: Sparkles, color: 'bg-primary-50 text-primary-700' },
  translate: { icon: Languages, color: 'bg-info-light text-info' },
  subtitle: { icon: Captions, color: 'bg-warning-light text-warning' },
  podcast: { icon: Podcast, color: 'bg-success-light text-success' },
};
const ALIASES: Record<string, string> = { chat: 'general', article: 'translate', video: 'subtitle' };

function style(icon: string) {
  return ICONS[ALIASES[icon] ?? icon] ?? { icon: Wand2, color: 'bg-bg-tertiary text-text-secondary' };
}

export function AgentIcon({ icon, className }: { icon: string; className?: string }) {
  const Icon = style(icon).icon;
  return <Icon aria-hidden className={cn('h-4 w-4 shrink-0', className)} />;
}

/** 带底色的 Agent 头像：每个 Agent 一个颜色，列表、对话页、卡片里都一样，好认 */
export function AgentAvatar({ icon, size = 'md', className }: { icon: string; size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const { icon: Icon, color } = style(icon);
  const box = { sm: 'h-7 w-7 rounded-md', md: 'h-9 w-9 rounded-lg', lg: 'h-11 w-11 rounded-xl' }[size];
  const glyph = { sm: 'h-3.5 w-3.5', md: 'h-4.5 w-4.5', lg: 'h-5 w-5' }[size];
  return (
    <span aria-hidden className={cn('inline-flex shrink-0 items-center justify-center', box, color, className)}>
      <Icon className={glyph} />
    </span>
  );
}
