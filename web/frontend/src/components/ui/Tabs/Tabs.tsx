import { cn } from '../../../shared/utils';

export interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
  variant?: 'underline' | 'pills' | 'segmented';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeStyles = {
  sm: 'text-sm px-3 py-1.5',
  md: 'text-base px-4 py-2',
  lg: 'text-lg px-5 py-2.5',
};

export function Tabs({
  tabs,
  activeTab,
  onChange,
  variant = 'underline',
  size = 'md',
  className,
}: TabsProps) {
  return (
    <div className={cn('w-full', className)}>
      <div
        className={cn(
          'flex',
          variant === 'underline' && 'border-b border-border-subtle/50',
          variant === 'pills' && 'gap-2 p-1.5',
          variant === 'segmented' && 'bg-gradient-to-br from-bg-tertiary to-bg-hover p-1.5 rounded-xl inline-flex shadow-inner'
        )}
      >
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => !tab.disabled && onChange(tab.id)}
            disabled={tab.disabled}
            className={cn(
              'relative flex items-center gap-2.5 font-medium transition-all duration-300',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              sizeStyles[size],
              variant === 'underline' && [
                'border-b-2 -mb-px',
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-text-muted hover:text-text-primary',
              ],
              variant === 'pills' && [
                'rounded-xl',
                activeTab === tab.id
                  ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-lg shadow-primary-500/30 ring-1 ring-primary-300/40'
                  : 'text-text-secondary hover:text-text-primary hover:bg-white/50',
              ],
              variant === 'segmented' && [
                'rounded-lg flex-1 justify-center',
                activeTab === tab.id
                  ? 'bg-gradient-to-br from-white to-white/80 text-text-primary shadow-md'
                  : 'text-text-muted hover:text-text-primary',
              ]
            )}
          >
            {tab.icon && <span className="relative z-10 flex-shrink-0">{tab.icon}</span>}
            <span className="relative z-10">{tab.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * 带面板的标签页组件
 */
export interface TabsWithPanelProps extends Omit<TabsProps, 'className'> {
  className?: string;
  tabsClassName?: string;
  panelsClassName?: string;
  renderPanel: (tabId: string) => React.ReactNode;
}

export function TabsWithPanel({
  tabs,
  activeTab,
  onChange,
  variant = 'underline',
  size = 'md',
  renderPanel,
  className,
  tabsClassName,
  panelsClassName,
}: TabsWithPanelProps) {
  return (
    <div className={className}>
      <Tabs
        tabs={tabs}
        activeTab={activeTab}
        onChange={onChange}
        variant={variant}
        size={size}
        className={tabsClassName}
      />
      <div className={cn('mt-6 animate-fade-in', panelsClassName)}>
        {renderPanel(activeTab)}
      </div>
    </div>
  );
}
