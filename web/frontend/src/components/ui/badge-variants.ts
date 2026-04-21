import { cva, type VariantProps } from "class-variance-authority"

export const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all",
  {
    variants: {
      variant: {
        default: "bg-gray-100 text-gray-700 hover:bg-gray-200",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground border",
        success: "bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 border border-green-200",
        warning: "bg-gradient-to-r from-amber-50 to-orange-50 text-amber-700 border border-amber-200",
        error: "bg-gradient-to-r from-red-50 to-rose-50 text-red-700 border border-red-200",
        info: "bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200",
        primary: "bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-colored",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export type BadgeVariantProps = VariantProps<typeof badgeVariants>
