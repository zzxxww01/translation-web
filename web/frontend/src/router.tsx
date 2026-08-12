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
// 78bcf2c 把确认工作台换成沉浸式模式时，连带删掉了质量报告页的路由，但侧栏的
// 「查看质量报告」按钮（DocumentSidebar）和 DocumentQualityPanel 的入口链接都还
// 指向这个路径——于是点了之后被静默重定向进沉浸式编辑器，整条质量报告链路
// （前端页面 + 后端 quality_report 服务）实际不可达。这里把它接回来。
const QualityReportPage = lazy(() =>
  import('./features/quality-report/index').then(module => ({
    default: module.QualityReportPage,
  }))
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
        element: (
          <LazyPage>
            <QualityReportPage />
          </LazyPage>
        ),
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
