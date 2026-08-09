import { Suspense, lazy } from 'react';
import { createBrowserRouter, Navigate, RouterProvider, useParams } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { NotFoundPage } from './components/layout/NotFoundPage';

const DocumentFeature = lazy(() =>
  import('./features/document/index.tsx').then(module => ({ default: module.DocumentFeature }))
);
const GlossaryFeature = lazy(() =>
  import('./features/glossary/index.tsx').then(module => ({ default: module.GlossaryFeature }))
);
const PostFeature = lazy(() =>
  import('./features/post/index.tsx').then(module => ({ default: module.PostFeature }))
);
const WechatFeature = lazy(() =>
  import('./features/wechat/index.tsx').then(module => ({ default: module.WechatFeature }))
);
const SlackFeature = lazy(() =>
  import('./features/slack/index.tsx').then(module => ({ default: module.SlackFeature }))
);
const ToolsFeature = lazy(() =>
  import('./features/tools/index.tsx').then(module => ({ default: module.ToolsFeature }))
);
function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    </div>
  );
}

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>;
}

function LegacyDocumentWorkflowRedirect() {
  const { projectId = '' } = useParams<{ projectId: string }>();
  return <Navigate to={`/document/${projectId}?mode=immersive`} replace />;
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/document" replace />,
      },
      {
        path: 'document/:projectId/confirmation',
        element: <LegacyDocumentWorkflowRedirect />,
      },
      {
        path: 'document/:projectId/quality-report',
        element: <LegacyDocumentWorkflowRedirect />,
      },
      {
        path: 'document/:projectId?/:sectionId?',
        element: (
          <LazyPage>
            <DocumentFeature />
          </LazyPage>
        ),
      },
      {
        path: 'post',
        element: (
          <LazyPage>
            <PostFeature />
          </LazyPage>
        ),
      },
      {
        path: 'wechat',
        element: (
          <LazyPage>
            <WechatFeature />
          </LazyPage>
        ),
      },
      {
        path: 'glossary',
        element: (
          <LazyPage>
            <GlossaryFeature />
          </LazyPage>
        ),
      },
      {
        path: 'slack',
        element: (
          <LazyPage>
            <SlackFeature />
          </LazyPage>
        ),
      },
      {
        path: 'tools',
        element: (
          <LazyPage>
            <ToolsFeature />
          </LazyPage>
        ),
      },
      // Legacy route — redirect to new nested route
      {
        path: 'confirmation/:projectId',
        element: <LegacyDocumentWorkflowRedirect />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
