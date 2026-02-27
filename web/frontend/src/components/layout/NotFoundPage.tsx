/**
 * 404 页面组件
 */

import { Link } from 'react-router-dom';
import { Home, ArrowLeft } from 'lucide-react';
import { Button } from '../ui';

export function NotFoundPage() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <div className="mb-6 text-8xl font-bold text-text-muted/30">404</div>
        <h1 className="mb-2 text-2xl font-bold text-text-primary">页面未找到</h1>
        <p className="mb-8 text-text-muted">抱歉，您访问的页面不存在</p>
        <div className="flex justify-center gap-4">
          <Link to="/">
            <Button
              variant="primary"
              leftIcon={<Home className="h-4 w-4" />}
            >
              返回首页
            </Button>
          </Link>
          <Button
            variant="secondary"
            onClick={() => window.history.back()}
            leftIcon={<ArrowLeft className="h-4 w-4" />}
          >
            返回上一页
          </Button>
        </div>
      </div>
    </div>
  );
}
