/**
 * 应用布局组件
 * 包含头部导航和内容出口
 */

import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sparkles, BookOpen } from 'lucide-react';
import { FeatureNav } from './FeatureNav';
import { GlossaryModal } from '../../features/confirmation/components/GlossaryModal';

export function AppLayout() {
  const [isGlossaryOpen, setIsGlossaryOpen] = useState(false);

  return (
    <div className="flex h-screen flex-col">
      {/* 头部导航 */}
      <header className="glass-effect sticky top-0 z-40 border-b border-border-subtle/50">
        <div className="flex h-16 items-center justify-between px-6">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 shadow-lg shadow-primary-500/30">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <h1 className="bg-gradient-to-br from-primary-600 to-primary-400 bg-clip-text text-xl font-bold text-transparent">
              Translation Agent
            </h1>
          </div>

          {/* 功能导航 */}
          <FeatureNav />

          {/* 术语库按钮 */}
          <button
            onClick={() => setIsGlossaryOpen(true)}
            className="rounded-lg p-2 text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors"
            title="术语库"
          >
            <BookOpen className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* 主内容区 - 路由出口 */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      {/* 全局术语库模态框 */}
      <GlossaryModal
        isOpen={isGlossaryOpen}
        onClose={() => setIsGlossaryOpen(false)}
      />
    </div>
  );
}
