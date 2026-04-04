import { Link } from 'react-router-dom';
import { Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <div className="mb-6 text-8xl font-bold text-muted-foreground/30">404</div>
        <h1 className="mb-2 text-2xl font-bold">页面未找到</h1>
        <p className="mb-8 text-muted-foreground">抱歉，您访问的页面不存在</p>
        <div className="flex justify-center gap-4">
          <Button asChild>
            <Link to="/">
              <Home className="h-4 w-4" />
              返回首页
            </Link>
          </Button>
          <Button variant="outline" onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4" />
            返回上一页
          </Button>
        </div>
      </div>
    </div>
  );
}
