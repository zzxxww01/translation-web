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

function BrandMark({ showTagline = true }: { showTagline?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span
        aria-hidden="true"
        className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-500 text-[15px] leading-none text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.15)]"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        译
      </span>
      <span
        className="text-[19px] font-semibold leading-none tracking-tight text-text-primary"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        momo
      </span>
      {showTagline && <span className="sr-only">翻译工作台</span>}
    </div>
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

  const handleGlossaryClick = () => {
    if (isGlossaryRoute) return;

    const params = new URLSearchParams();
    const routeProjectId = isDocumentRoute ? currentProjectId : confirmationProjectId;

    params.set('from', `${location.pathname}${location.search}`);
    if (routeProjectId) {
      params.set('projectId', routeProjectId);
      params.set('scope', 'project');
    }
    navigate({
      pathname: '/glossary',
      search: params.toString(),
    });
  };

  return (
    <HeaderSlotContext.Provider value={slot}>
    <div className="relative flex h-screen flex-col overflow-hidden bg-background">
      {/* 顶栏：品牌 + 导航靠左，右边是当前页面自己的操作（PageActions 放进来）和全局按钮；各页面不再另占一行标题栏 */}
      {!isImmersiveMode && !isWorkbenchRoute && (
        <header className="relative z-40 shrink-0 border-b border-border-subtle bg-white/85 backdrop-blur-md">
          <div className="flex h-12 items-center gap-3 px-3 md:px-5">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8 md:hidden" aria-label="打开功能导航">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-72 bg-[#fbf8f6]">
                <SheetHeader>
                  <SheetTitle>
                    <BrandMark showTagline={false} />
                  </SheetTitle>
                </SheetHeader>
                <Separator className="my-4" />
                <FeatureNav orientation="vertical" onNavigate={() => setMobileOpen(false)} />
              </SheetContent>
            </Sheet>

            <Link to="/articles" aria-label="momo 翻译工作台首页" className="shrink-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <BrandMark />
            </Link>

            <div className="hidden h-full md:flex">
              <FeatureNav />
            </div>

            {/* 当前页面的操作 */}
            <div ref={setSlot} className="ml-auto flex min-w-0 items-center justify-end gap-2" />

            <div className="flex shrink-0 items-center gap-1">
              <GlobalTaskIndicator />
              <Button
                variant={isGlossaryRoute ? 'secondary' : 'ghost'}
                size="sm"
                className="h-8 px-2"
                onClick={handleGlossaryClick}
                title="术语管理"
                aria-label="术语与规则管理"
              >
                <BookOpen className="h-4 w-4" />
                <span className="hidden xl:inline">术语库</span>
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
