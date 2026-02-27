import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '../../../shared/utils';

/**
 * 按钮变体类型
 */
export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';

/**
 * 按钮尺寸类型
 */
export type ButtonSize = 'sm' | 'md' | 'lg';

/**
 * 按钮组件属性
 */
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-br from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 shadow-lg shadow-primary-500/30 hover:shadow-xl hover:shadow-primary-500/40',
  secondary: 'bg-gradient-to-br from-bg-tertiary to-bg-hover text-text-primary hover:from-bg-hover hover:to-bg-tertiary shadow-sm hover:shadow-md',
  outline: 'border-2 border-border text-text-primary hover:border-primary-400 hover:text-primary-600 hover:bg-primary-50/50',
  ghost: 'text-text-secondary hover:text-text-primary hover:bg-gradient-to-br hover:from-bg-tertiary hover:to-primary-50/30',
  danger: 'bg-gradient-to-br from-error to-error/90 text-white hover:from-error/90 hover:to-error shadow-lg shadow-error/30',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3.5 py-2 text-sm rounded-lg min-h-[36px]',
  md: 'px-5 py-2.5 text-base rounded-xl min-h-[44px]',
  lg: 'px-7 py-3.5 text-lg rounded-2xl min-h-[52px]',
};

/**
 * 按钮组件
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-1.5 font-semibold whitespace-nowrap',
          'transition-all duration-300',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'relative overflow-hidden',
          'hover:-translate-y-0.5 hover:scale-[1.02] active:translate-y-0 active:scale-100',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {/* 悬浮光晕效果 */}
        <span className="absolute inset-0 rounded-inherit bg-gradient-to-r from-white/20 via-transparent to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

        {isLoading ? (
          <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          leftIcon
        )}
        <span className="relative">{children}</span>
        {rightIcon && !isLoading && <span className="relative">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
