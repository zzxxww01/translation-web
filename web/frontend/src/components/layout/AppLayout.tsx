import { Link, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, Menu } from 'lucide-react';
import { FeatureNav } from './FeatureNav';
import { useDocumentStore } from '@/shared/stores';
import { Button } from '@/components/ui/Button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';
import { useState } from 'react';
import { HeaderSlotContext } from './headerSlotContext';
import { GlobalTaskIndicator } from './GlobalTaskIndicator';

/** 左上角只放「译」字标志，不写产品名（2026-11-22 用户：不需要名字） */
function BrandMark() {
  return (
    <span
      aria-hidden="true"
      className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-500 text-[15px] leading-none text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.15)]"
      style={{ fontFamily: 'var(--font-display)' }}
    >
      译
    </span>
  );
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
          {/* 手机：菜单 + 标 + 页面操作（占满剩下的宽度）；桌面：三列，导航居中 */}
          <div className="flex h-14 items-center gap-2 px-3 md:grid md:grid-cols-[1fr_auto_1fr] md:gap-3 md:px-6">
          {/* Logo + Mobile menu */}
          <div className="flex shrink-0 items-center gap-1.5 md:gap-3">
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
                  <SheetTitle className="flex items-center gap-2 text-base">
                    <BrandMark />
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

            <Link to="/articles" aria-label="回到首页" className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <BrandMark />
            </Link>
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
