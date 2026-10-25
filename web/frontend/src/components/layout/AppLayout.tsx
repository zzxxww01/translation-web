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
import { GlobalTaskIndicator } from './GlobalTaskIndicator';

function BrandMark({ showTagline = true }: { showTagline?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        aria-hidden="true"
        className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-500 text-[17px] leading-none text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.15)]"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        译
      </span>
      <span className="flex items-baseline gap-2">
        <span
          className="text-[22px] font-semibold leading-none tracking-tight text-text-primary"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          momo
        </span>
        {showTagline && (
          <span className="hidden text-[13px] text-text-muted lg:inline">/ 翻译工作台</span>
        )}
      </span>
    </div>
  );
}

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isImmersiveMode =
    searchParams.get('immersive') === '1' || searchParams.get('mode') === 'immersive';
  const isDocumentRoute = location.pathname.startsWith('/document');
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
    <div className="relative flex h-screen flex-col overflow-hidden bg-background">
      {/* Header */}
      {!isImmersiveMode && (
        <header className="relative sticky top-0 z-40 border-b border-border-subtle bg-[#fbf8f6]/90 backdrop-blur-md">
          <div className="flex h-16 items-center justify-between px-4 md:px-8">
          {/* Logo + Mobile menu */}
          <div className="flex items-center gap-3">
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
              <SheetContent side="left" className="w-72 bg-[#fbf8f6]">
                <SheetHeader>
                  <SheetTitle>
                    <BrandMark showTagline={false} />
                  </SheetTitle>
                </SheetHeader>
                <Separator className="my-4" />
                <FeatureNav
                  orientation="vertical"
                  onNavigate={() => setMobileOpen(false)}
                />
              </SheetContent>
            </Sheet>

            <Link to="/articles" aria-label="momo 翻译工作台首页" className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <BrandMark />
            </Link>
          </div>

          {/* Desktop nav */}
          <div className="hidden self-stretch md:flex">
            <FeatureNav />
          </div>

          {/* Right side */}
          <div className="flex items-center gap-1">
            <GlobalTaskIndicator />
            <Button
              variant={isGlossaryRoute ? 'secondary' : 'ghost'}
              size="sm"
              className="h-9 px-2.5 lg:px-3"
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
  );
}
