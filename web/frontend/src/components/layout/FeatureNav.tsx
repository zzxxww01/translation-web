import { NavLink } from 'react-router-dom';
import { BookOpen, MessageSquare, MessageCircle, Wrench, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/document', label: '长文翻译', icon: <BookOpen className="h-4 w-4" /> },
  { path: '/post', label: '帖子翻译', icon: <MessageSquare className="h-4 w-4" /> },
  { path: '/wechat', label: '微信排版', icon: <FileText className="h-4 w-4" /> },
  { path: '/slack', label: 'Slack 回复', icon: <MessageCircle className="h-4 w-4" /> },
  { path: '/tools', label: '工具箱', icon: <Wrench className="h-4 w-4" /> },
];

interface FeatureNavProps {
  orientation?: 'horizontal' | 'vertical';
  onNavigate?: () => void;
}

export function FeatureNav({ orientation = 'horizontal', onNavigate }: FeatureNavProps) {
  const isVertical = orientation === 'vertical';

  return (
    <nav className={cn(
      'flex gap-1',
      isVertical
        ? 'flex-col'
        : 'items-center rounded-md border border-slate-200 bg-slate-50/90 p-0.5 shadow-inner shadow-white/80'
    )}>
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md text-sm font-medium leading-none transition-colors',
              isVertical ? 'px-3 py-2' : 'h-8 px-2.5 py-1.5',
              isVertical && 'w-full border border-transparent',
              isActive
                ? 'bg-white text-slate-950 shadow-sm ring-1 ring-slate-200/70'
                : 'text-slate-500 hover:bg-white/80 hover:text-slate-950'
            )
          }
        >
          {item.icon}
          <span className="flex h-4 items-center leading-none">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export type FeatureTab = 'document' | 'post' | 'wechat' | 'slack' | 'tools';
