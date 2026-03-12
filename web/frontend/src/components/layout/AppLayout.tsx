/**
 * Application layout component with header navigation and routed content.
 */

import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { BookOpen, Sparkles } from 'lucide-react';
import { FeatureNav } from './FeatureNav';
import { useDocumentStore } from '../../shared/stores';

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const isDocumentRoute = location.pathname.startsWith('/document');
  const isGlossaryRoute = location.pathname.startsWith('/glossary');
  const currentProjectId = useDocumentStore(state => state.currentProject?.id);
  const confirmationProjectId =
    location.pathname.match(/^\/confirmation\/([^/]+)/)?.[1] ?? null;

  const handleGlossaryClick = () => {
    if (isGlossaryRoute) {
      return;
    }

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

  const glossaryButtonClass = isGlossaryRoute
    ? 'bg-primary/10 text-primary'
    : 'text-text-secondary hover:bg-primary/10 hover:text-primary';

  return (
    <div className="flex h-screen flex-col">
      <header className="glass-effect sticky top-0 z-40 border-b border-border-subtle/50">
        <div className="flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 shadow-lg shadow-primary-500/30">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <h1 className="bg-gradient-to-br from-primary-600 to-primary-400 bg-clip-text text-xl font-bold text-transparent">
              Translation Agent
            </h1>
          </div>

          <FeatureNav />

          <button
            onClick={handleGlossaryClick}
            className={`rounded-lg p-2 transition-colors ${glossaryButtonClass}`}
            title={'\u672F\u8BED\u7BA1\u7406'}
          >
            <BookOpen className="h-5 w-5" />
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
