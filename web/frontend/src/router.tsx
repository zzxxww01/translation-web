/**
 * 路由配置
 * 使用 React Router DOM 实现客户端路由
 */

import { createBrowserRouter, Navigate, RouterProvider, useParams } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DocumentFeature } from './features/document';
import { PostFeature } from './features/post';
import { SlackFeature } from './features/slack';
import { ToolsFeature } from './features/tools';
import { ConfirmationFeature } from './features/confirmation';
import { NotFoundPage } from './components/layout/NotFoundPage';

// 分段确认工作流路由包装组件
function ConfirmationRoute() {
  // 使用 window.location 获取 projectId
  const { projectId = '' } = useParams<{ projectId: string }>();
  return <ConfirmationFeature projectId={projectId} />;
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
        element: <DocumentFeature />,
      },
      {
        path: 'post',
        element: <PostFeature />,
      },
      {
        path: 'slack',
        element: <SlackFeature />,
      },
      {
        path: 'tools',
        element: <ToolsFeature />,
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
