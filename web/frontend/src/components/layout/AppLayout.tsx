import { Link, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, Menu } from 'lucide-react';
import { FeatureNav } from './FeatureNav';
import { NAV_ITEMS } from './navItems';
import { useDocumentStore } from '@/shared/stores';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';
import { useEffect, useState } from 'react';
import { HeaderSlotContext } from './headerSlotContext';
import { GlobalTaskIndicator } from './GlobalTaskIndicator';

/**
 * 左上角的衬线字标「Leaf」（2026-11-23 用户定名：书页的一张，翻页的「翻」）。
 * 不加色块，导航居中（用户要求）。标签页图标仍是「译」字（favicon.svg）。
 */
const BRAND_NAME = 'Leaf';

function BrandMark() {
  return (
    <span
      aria-hidden="true"
      className="select-none text-xl font-semibold leading-none tracking-[0.01em] text-primary-600"
      style={{ fontFamily: 'var(--font-display)' }}
    >
      {BRAND_NAME}
    </span>
  );
}

function BrandDivider({ className }: { className?: string }) {
  return <span aria-hidden="true" className={cn('h-4 w-px shrink-0 bg-border', className)} />;
}

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [slot, setSlot] = useState<HTMLDivElement | null>(null);
  const isImmersiveMode =
    searchParams.get('immersive') === '1' || searchParams.get('mode') === 'immersive';
  const isDocumentRoute = location.pathname.startsWith('/document');
  // 文章工作台自己的顶栏就是整页顶栏，功能导航收在它左上角的菜单里（设计文档 6.1，方案 A）
  const isWorkbenchRoute = /^\/articles\/[^/]+/.test(location.pathname);
  const isGlossaryRoute = location.pathname.startsWith('/glossary');
  // 手机上导航收进菜单，标志旁边写出当前在哪一页
  const currentPageLabel = isGlossaryRoute
    ? '术语库'
    : NAV_ITEMS.find(item => location.pathname.startsWith(item.path))?.label;
  useEffect(() => {
    document.title = currentPageLabel ? `${currentPageLabel} · ${BRAND_NAME}` : BRAND_NAME;
  }, [currentPageLabel]);
  const currentProjectId = useDocumentStore(state => state.currentProject?.id);
  const confirmationProjectId =
    location.pathname.match(/^\/confirmation\/([^/]+)/)?.[1] ??
    location.pathname.match(/^\/document\/([^/]+)\/confirmation/)?.[1] ??
    null;

  // 术语库是顶栏右侧的单独按钮，不占导航 tab；带上 from 能一键回来，从长文编辑器进去时带上项目
  const handleGlossaryClick = () => {
    if (isGlossaryRoute) return;
    const params = new URLSearchParams({ from: `${location.pathname}${location.search}` });
    const routeProjectId = isDocumentRoute ? currentProjectId : confirmationProjectId;
    if (routeProjectId) {
      params.set('projectId', routeProjectId);
      params.set('scope', 'project');
    }
    navigate({ pathname: '/glossary', search: params.toString() });
  };

  return (
    <HeaderSlotContext.Provider value={slot}>
    <div className="relative flex h-screen flex-col overflow-hidden bg-background">
      {/* Header */}
      {!isImmersiveMode && !isWorkbenchRoute && (
        <header className="sticky top-0 z-40 border-b border-border-subtle bg-bg-primary/90 backdrop-blur-md">
          {/* 手机：菜单 + 标 │ 当前页名 + 页面操作；桌面：三列，导航居中 */}
          <div className="flex h-14 items-center gap-2 px-3 md:grid md:grid-cols-[1fr_auto_1fr] md:gap-3 md:px-6">
          {/* Logo + Mobile menu */}
          <div className="flex shrink-0 items-center gap-2 md:gap-4">
            {/* Mobile menu */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="md:hidden"
                  aria-label="打开功能导航"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-72">
                <SheetHeader>
                  <SheetTitle className="flex items-center gap-3 text-base">
                    <BrandMark />
                    <BrandDivider />
                    功能
                  </SheetTitle>
                </SheetHeader>
                <Separator className="my-4" />
                <FeatureNav
                  orientation="vertical"
                  onNavigate={() => setMobileOpen(false)}
                />
              </SheetContent>
            </Sheet>

            <Link to="/articles" aria-label="回到首页" className="flex items-center rounded-md px-1 py-1 transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:-ml-1">
              <BrandMark />
            </Link>
            {currentPageLabel && <BrandDivider className="md:hidden" />}
            {currentPageLabel && (
              <span className="truncate text-sm font-medium text-text-primary md:hidden">
                {currentPageLabel}
              </span>
            )}
          </div>

          {/* Desktop nav */}
          <div className="hidden self-stretch md:flex">
            <FeatureNav />
          </div>

          {/* Right side：当前页面的操作（PageActions 放进来，页面不再另占一行标题栏）+ 全局按钮 */}
          <div className="flex min-w-0 flex-1 items-center justify-end gap-1">
            <div ref={setSlot} className="flex min-w-0 items-center justify-end gap-2" />
            <GlobalTaskIndicator />
            <Button
              variant={isGlossaryRoute ? 'secondary' : 'ghost'}
              size="sm"
              className="h-9 shrink-0 px-2.5 lg:px-3"
              onClick={handleGlossaryClick}
              title="术语管理"
              aria-label="术语与规则管理"
            >
              <BookOpen className="h-4 w-4" />
              <span className="hidden lg:inline">术语库</span>
            </Button>
          </div>
        </div>
      </header>
      )}

      <main className="relative z-10 flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
    </HeaderSlotContext.Provider>
  );
}
