import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type HTMLAttributes,
  type InputHTMLAttributes,
} from 'react';
import { cn } from '../../../shared/utils';

interface RadioGroupContextValue {
  value: string;
  name?: string;
  onValueChange?: (value: string) => void;
}

const RadioGroupContext = createContext<RadioGroupContextValue | null>(null);

export interface RadioGroupProps extends HTMLAttributes<HTMLDivElement> {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  name?: string;
}

export function RadioGroup({
  value,
  defaultValue = '',
  onValueChange,
  name,
  className,
  children,
  ...props
}: RadioGroupProps) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const currentValue = value ?? internalValue;

  const handleChange = useCallback(
    (nextValue: string) => {
      if (value === undefined) {
        setInternalValue(nextValue);
      }
      onValueChange?.(nextValue);
    },
    [onValueChange, value]
  );

  const contextValue = useMemo(
    () => ({ value: currentValue, name, onValueChange: handleChange }),
    [currentValue, handleChange, name]
  );

  return (
    <RadioGroupContext.Provider value={contextValue}>
      <div role="radiogroup" className={cn('space-y-2', className)} {...props}>
        {children}
      </div>
    </RadioGroupContext.Provider>
  );
}

export interface RadioGroupItemProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  value: string;
}

export function RadioGroupItem({
  value,
  className,
  id,
  disabled,
  ...props
}: RadioGroupItemProps) {
  const context = useContext(RadioGroupContext);
  const checked = context?.value === value;
  const name = context?.name;

  return (
    <input
      type="radio"
      id={id}
      name={name}
      value={value}
      checked={checked}
      disabled={disabled}
      onChange={() => context?.onValueChange?.(value)}
      className={cn(
        'h-4 w-4 rounded-full border border-border text-primary-600 focus:ring-2 focus:ring-primary-500',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  );
}
