/**
 * 功能导航组件
 * 使用 React Router 的 NavLink 实现路由导航
 */

import { NavLink } from 'react-router-dom';
import { BookOpen, MessageSquare, MessageCircle, Wrench } from 'lucide-react';
import { cn } from '../../shared/utils';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/document', label: '长文翻译', icon: <BookOpen className="h-5 w-5" /> },
  { path: '/post', label: '帖子翻译', icon: <MessageSquare className="h-5 w-5" /> },
  { path: '/slack', label: 'Slack 回复', icon: <MessageCircle className="h-5 w-5" /> },
  { path: '/tools', label: '工具箱', icon: <Wrench className="h-5 w-5" /> },
];

export function FeatureNav() {
  return (
    <nav className="flex items-center gap-1">
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2.5 rounded-xl px-5 py-2.5 text-base font-medium transition-all duration-200',
              isActive
                ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-lg shadow-primary-500/30'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
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

// 保持向后兼容的导出
export type FeatureTab = 'document' | 'post' | 'slack' | 'tools';
