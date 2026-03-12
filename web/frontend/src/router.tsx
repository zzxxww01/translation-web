/**
 * 路由配置
 * 使用 React Router DOM 实现客户端路由
 */

import { Suspense, lazy } from 'react';
import { createBrowserRouter, Navigate, RouterProvider, useParams } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { NotFoundPage } from './components/layout/NotFoundPage';

const DocumentFeature = lazy(() =>
  import('./features/document/index.tsx').then(module => ({ default: module.DocumentFeature }))
);
const GlossaryFeature = lazy(() =>
  import('./features/GlossaryFeature.tsx').then(module => ({ default: module.GlossaryFeature }))
);
const PostFeature = lazy(() =>
  import('./features/post/index.tsx').then(module => ({ default: module.PostFeature }))
);
const SlackFeature = lazy(() =>
  import('./features/slack/index.tsx').then(module => ({ default: module.SlackFeature }))
);
const ToolsFeature = lazy(() =>
  import('./features/tools/index.tsx').then(module => ({ default: module.ToolsFeature }))
);
const ConfirmationFeature = lazy(() =>
  import('./features/confirmation/index.tsx').then(module => ({
    default: module.ConfirmationFeature,
  }))
);

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
    </div>
  );
}

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>;
}

// 分段确认工作流路由包装组件
function ConfirmationRoute() {
  const { projectId = '' } = useParams<{ projectId: string }>();
  return (
    <LazyPage>
      <ConfirmationFeature projectId={projectId} />
    </LazyPage>
  );
}

/**
 * 应用路由配置
 */
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
        path: 'document',
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
      {
        path: 'confirmation/:projectId',
        element: <ConfirmationRoute />,
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
