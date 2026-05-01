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
      isVertical ? 'flex-col' : 'items-center'
    )}>
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isVertical && 'w-full',
              isActive
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )
          }
        >
          {item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export type FeatureTab = 'document' | 'post' | 'wechat' | 'slack' | 'tools';
