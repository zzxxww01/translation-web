import { isRouteErrorResponse, Link, useRouteError } from 'react-router-dom';
import { ArrowLeft, Home, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

/** 404、出错等整页提示：同一种排版，标题宋体，下面一句说明和两个按钮 */
function StatusPage({ code, title, detail, retry }: { code: string; title: string; detail: string; retry?: boolean }) {
  return (
    <div className="flex h-full min-h-[60vh] items-center justify-center p-6">
      <div className="max-w-md text-center">
        <div className="mb-4 font-[family-name:var(--font-display)] text-5xl text-text-disabled">{code}</div>
        <h1 className="mb-2 text-xl text-text-primary">{title}</h1>
        <p className="mb-6 break-words text-sm leading-relaxed text-text-muted">{detail}</p>
        <div className="flex justify-center gap-2">
          {retry ? (
            <Button onClick={() => window.location.reload()}>
              <RefreshCw />
              刷新页面
            </Button>
          ) : (
            <Button asChild>
              <Link to="/"><Home />回到首页</Link>
            </Button>
          )}
          <Button variant="outline" onClick={() => window.history.back()}>
            <ArrowLeft />
            返回上一页
          </Button>
        </div>
      </div>
    </div>
  );
}

export function NotFoundPage() {
  return <StatusPage code="404" title="页面不存在" detail="地址可能写错了，或者这一页已经搬走了。" />;
}

/** 路由里渲染出错时显示（替代 React Router 默认的英文开发者错误页） */
export function RouteErrorPage() {
  const error = useRouteError();
  console.error('Route error:', error);
  if (isRouteErrorResponse(error) && error.status === 404) return <NotFoundPage />;
  const message = error instanceof Error ? error.message : isRouteErrorResponse(error) ? error.statusText : '';
  return (
    <StatusPage
      code="出错了"
      title="这一页没能显示出来"
      detail={message ? `错误信息：${message}。刷新通常就好；一直这样请把这句话发给维护的人。` : '刷新通常就好；一直这样请联系维护的人。'}
      retry
    />
  );
}
