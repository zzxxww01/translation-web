import { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { NAV_ITEMS as navItems, type NavItem } from './navItems';

// 各 tab 上次停留的地址（含查询参数）；只在本页会话内有效
const lastLocation = new Map<string, string>();

interface FeatureNavProps {
  orientation?: 'horizontal' | 'vertical';
  onNavigate?: () => void;
}

export function FeatureNav({ orientation = 'horizontal', onNavigate }: FeatureNavProps) {
  const isVertical = orientation === 'vertical';
  const { pathname, search } = useLocation();
  const current = navItems.find(item => item.remember && pathname === item.path);
  useEffect(() => {
    if (current) lastLocation.set(current.path, `${pathname}${search}`);
  }, [current, pathname, search]);
  // 当前所在的 tab 再点一次回到它的首页
  const target = (item: NavItem) => {
    return item === current ? item.path : lastLocation.get(item.path) ?? item.path;
  };

  return (
    <nav aria-label="主要功能" className={cn(
      'flex',
      isVertical ? 'flex-col gap-1' : 'h-full items-stretch gap-1'
    )}>
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={target(item)}
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
                    // 横向导航：当前页是浅梅子色药丸（2026-11-23 从底部下划线改来）
                    'flex h-8 items-center self-center rounded-full px-3 transition-colors xl:px-3.5',
                    isActive
                      ? 'bg-primary-50 font-medium text-primary-700'
                      : 'text-text-muted hover:bg-ink-wash hover:text-text-primary'
                  )
            )
          }
        >
          {isVertical && <item.icon className="h-4 w-4" />}
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export type FeatureTab = 'document' | 'substack' | 'post' | 'wechat' | 'slack' | 'glossary' | 'tools' | 'skills';
