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
import { GlobalTaskTray } from './GlobalTaskTray';

function Breadcrumbs() {
  const location = useLocation();
  const currentProject = useDocumentStore(state => state.currentProject);
  const currentSection = useDocumentStore(state => state.currentSection);
  const parts = location.pathname.split('/').filter(Boolean);

  const crumbs: { label: string; path?: string }[] = [];

  if (parts[0] === 'document') {
    crumbs.push({ label: '长文翻译', path: '/document' });
    if (parts[1]) {
      crumbs.push({
        label: currentProject?.id === parts[1] ? currentProject.title || '项目' : '项目',
        path: `/document/${parts[1]}`,
      });
    }
    if (parts[2] && !['confirmation', 'quality-report'].includes(parts[2])) {
      crumbs.push({
        label:
          currentSection?.section_id === parts[2]
            ? currentSection.title || '章节'
            : '章节',
      });
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
    <div className="flex items-center gap-1 text-sm text-muted-foreground">
      {crumbs.map((crumb, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="h-3 w-3" />}
          <span className={cn(
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

        {/* Breadcrumbs */}
        <div className="px-4 pb-2 md:px-6">
          <Breadcrumbs />
        </div>
      </header>
      )}

      {!isImmersiveMode && <GlobalTaskTray />}

      <main className="relative z-10 flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
