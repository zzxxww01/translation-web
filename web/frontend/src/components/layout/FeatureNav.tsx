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
                    // 横向导航用底部 2px 梅子色下划线标出当前页，压在顶栏底边上
                    'relative flex items-center px-3 after:absolute after:inset-x-3 after:-bottom-px after:h-0.5 after:rounded-full after:transition-colors',
                    isActive
                      ? 'font-medium text-text-primary after:bg-primary-500'
                      : 'text-text-muted after:bg-transparent hover:text-text-primary hover:after:bg-border'
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
