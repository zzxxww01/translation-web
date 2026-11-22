import { cva, type VariantProps } from "class-variance-authority"

export const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-bg-inset text-text-secondary",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground border",
        success: "border border-success/20 bg-success-light text-green-700",
        warning: "border border-warning/25 bg-warning-light text-warning-text",
        error: "border border-error/20 bg-error-light text-error",
        info: "border border-info/20 bg-info-light text-info",
        primary: "bg-primary-500 text-white",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export type BadgeVariantProps = VariantProps<typeof badgeVariants>
