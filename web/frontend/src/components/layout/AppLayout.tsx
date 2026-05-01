import { Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, Sparkles, Menu, ChevronRight } from 'lucide-react';
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
import { cn } from '@/lib/utils';
import { useState } from 'react';

function Breadcrumbs() {
  const location = useLocation();
  const currentProject = useDocumentStore(state => state.currentProject);
  const parts = location.pathname.split('/').filter(Boolean);

  const crumbs: { label: string; path?: string }[] = [];

  if (parts[0] === 'document') {
    crumbs.push({ label: '长文翻译', path: '/document' });
    if (parts.length > 1 && parts[1] === 'confirmation' && currentProject) {
      crumbs.push({ label: currentProject.title || '项目' });
      crumbs.push({ label: '确认' });
    }
  } else if (parts[0] === 'confirmation') {
    crumbs.push({ label: '长文翻译', path: '/document' });
    if (currentProject) {
      crumbs.push({ label: currentProject.title || '项目' });
    }
    crumbs.push({ label: '确认' });
  } else if (parts[0] === 'post') {
    crumbs.push({ label: '帖子翻译' });
  } else if (parts[0] === 'wechat') {
    crumbs.push({ label: '微信排版' });
  } else if (parts[0] === 'slack') {
    crumbs.push({ label: 'Slack 回复' });
  } else if (parts[0] === 'tools') {
    crumbs.push({ label: '工具箱' });
  } else if (parts[0] === 'glossary') {
    crumbs.push({ label: '术语管理' });
  }

  if (crumbs.length <= 1) return null;

  return (
    <div className="flex min-w-0 items-center gap-1 truncate text-xs text-muted-foreground md:text-sm">
      {crumbs.map((crumb, i) => (
        <span key={i} className="flex min-w-0 items-center gap-1">
          {i > 0 && <ChevronRight className="h-3 w-3" />}
          <span className={cn(
            'truncate',
            i === crumbs.length - 1 ? 'text-foreground font-medium' : ''
          )}>
            {crumb.label}
          </span>
        </span>
      ))}
    </div>
  );
}

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isImmersiveMode = searchParams.get('immersive') === '1';
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
    <div className="safe-area-shell flex flex-col bg-background relative overflow-hidden">
      {/* 流动网格背景 */}
      <div className="absolute inset-0 gradient-mesh-fluid pointer-events-none" />

      {/* Header */}
      {!isImmersiveMode && (
        <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/92 backdrop-blur-md relative safe-area-x">
          <div className="flex h-12 items-center justify-between px-3 md:h-12 md:px-6">
          {/* Logo + Mobile menu */}
          <div className="flex items-center gap-3">
            {/* Mobile menu */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden" aria-label="打开导航">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-[82vw] max-w-80">
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
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-950 shadow-sm md:h-8 md:w-8">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <h1 className="hidden h-8 items-center text-base font-semibold leading-none text-slate-950 sm:flex" style={{ fontFamily: 'var(--font-display)' }}>
                Translation Agent
              </h1>
            </div>
          </div>

          {/* Desktop nav */}
          <div className="hidden md:flex">
            <FeatureNav />
          </div>

          {/* Right side */}
          <Button
            variant={isGlossaryRoute ? 'secondary' : 'ghost'}
            size="icon"
            onClick={handleGlossaryClick}
            title="术语管理"
            aria-label="术语管理"
          >
            <BookOpen className="h-5 w-5" />
          </Button>
        </div>

        {/* Breadcrumbs */}
        <div className="hidden min-h-5 overflow-hidden px-3 pb-1 md:block md:px-6">
          <Breadcrumbs />
        </div>
      </header>
      )}

      <main className="relative z-10 flex min-h-0 flex-1 flex-col overflow-auto safe-area-x safe-area-bottom">
        <Outlet />
      </main>
    </div>
  );
}
