import { type ReactNode } from 'react';

export interface AppHeaderProps {
  rightContent?: ReactNode;
}

export function AppHeader({ rightContent }: AppHeaderProps) {
  return (
    <header className="glass-effect sticky top-0 z-40 border-b border-border-subtle">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-text-primary">
            Translation Agent
          </h1>
        </div>

        {/* Feature Navigation */}
        <div className="flex-1 flex justify-center">
          {/* FeatureNav will be rendered by parent */}
        </div>

        {/* Right Content */}
        <div className="flex items-center gap-2">
          {rightContent}
        </div>
      </div>
    </header>
  );
}
