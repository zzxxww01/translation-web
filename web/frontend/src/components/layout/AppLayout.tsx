import { Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, Sparkles, Menu } from 'lucide-react';
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
        <header className="relative sticky top-0 z-40 border-b bg-white">
          <div className="flex h-14 items-center justify-between px-4 md:px-6">
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
              <SheetContent side="left" className="w-72 bg-white">
                <SheetHeader>
                  <SheetTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-primary" />
                    <span style={{ fontFamily: 'var(--font-display)' }}>Translation Agent</span>
                  </SheetTitle>
                </SheetHeader>
                <Separator className="my-4" />
                <FeatureNav
                  orientation="vertical"
                  onNavigate={() => setMobileOpen(false)}
                />
              </SheetContent>
            </Sheet>

            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <h1 className="hidden text-lg font-semibold text-foreground sm:block" style={{ fontFamily: 'var(--font-display)' }}>
                Translation Agent
              </h1>
            </div>
          </div>

          {/* Desktop nav */}
          <div className="hidden md:flex">
            <FeatureNav />
          </div>

          {/* Right side */}
          <div className="flex items-center gap-1">
            <GlobalTaskIndicator />
            <Button
              variant={isGlossaryRoute ? 'secondary' : 'ghost'}
              size="icon"
              onClick={handleGlossaryClick}
              title="术语管理"
              aria-label="术语与规则管理"
            >
              <BookOpen className="h-5 w-5" />
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
