import * as React from "react"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button, type ButtonProps } from "@/components/ui/button"

export interface ButtonExtendedProps extends ButtonProps {
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const ButtonExtended = React.forwardRef<HTMLButtonElement, ButtonExtendedProps>(
  ({ className, children, isLoading, leftIcon, rightIcon, disabled, ...props }, ref) => {
    return (
      <Button
        className={cn(className)}
        disabled={disabled || isLoading}
        ref={ref}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : leftIcon ? (
          leftIcon
        ) : null}
        {children}
        {!isLoading && rightIcon}
      </Button>
    )
  }
)
ButtonExtended.displayName = "ButtonExtended"

export { ButtonExtended, ButtonExtended as Button }
