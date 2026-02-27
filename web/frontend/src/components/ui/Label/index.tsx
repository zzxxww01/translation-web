import { forwardRef, type LabelHTMLAttributes } from 'react';
import { cn } from '../../../shared/utils';

export type LabelProps = LabelHTMLAttributes<HTMLLabelElement>;

export const Label = forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, ...props }, ref) => {
    return (
      <label
        ref={ref}
        className={cn('text-sm font-medium text-text-secondary', className)}
        {...props}
      />
    );
  }
);

Label.displayName = 'Label';
