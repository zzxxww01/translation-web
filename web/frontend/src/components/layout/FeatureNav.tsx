import { NavLink } from 'react-router-dom';
import { BookOpen, MessageSquare, MessageCircle, Wrench, FileText, Sparkles, Newspaper } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/document', label: '长文翻译', icon: <BookOpen className="h-4 w-4" /> },
  { path: '/substack', label: '文章库', icon: <Newspaper className="h-4 w-4" /> },
  { path: '/post', label: '帖子翻译', icon: <MessageSquare className="h-4 w-4" /> },
  { path: '/wechat', label: '微信排版', icon: <FileText className="h-4 w-4" /> },
  { path: '/slack', label: 'Slack 回复', icon: <MessageCircle className="h-4 w-4" /> },
  { path: '/tools', label: '工具箱', icon: <Wrench className="h-4 w-4" /> },
  { path: '/skills', label: 'Skill', icon: <Sparkles className="h-4 w-4" /> },
];

interface FeatureNavProps {
  orientation?: 'horizontal' | 'vertical';
  onNavigate?: () => void;
}

export function FeatureNav({ orientation = 'horizontal', onNavigate }: FeatureNavProps) {
  const isVertical = orientation === 'vertical';

  return (
    <nav aria-label="主要功能" className={cn(
      'flex',
      isVertical ? 'flex-col gap-1' : 'h-full items-stretch gap-1'
    )}>
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          onClick={onNavigate}
          aria-label={item.label}
          className={({ isActive }) =>
            cn(
              'text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              isVertical
                ? cn(
                    'flex w-full items-center gap-3 rounded-md px-3 py-2.5',
                    isActive
                      ? 'bg-primary-50 font-medium text-primary-700'
                      : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                  )
                : cn(
                    // 横向导航用底部 2px 梅子色下划线标出当前页，压在顶栏底边上
                    'relative flex items-center px-3 after:absolute after:inset-x-3 after:-bottom-px after:h-0.5 after:rounded-full after:transition-colors',
                    isActive
                      ? 'font-medium text-text-primary after:bg-primary-500'
                      : 'text-text-muted after:bg-transparent hover:text-text-primary hover:after:bg-border'
                  )
            )
          }
        >
          {isVertical && item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export type FeatureTab = 'document' | 'substack' | 'post' | 'wechat' | 'slack' | 'tools' | 'skills';
