import { cva, type VariantProps } from "class-variance-authority"

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-45 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "button-fluid",
        destructive:
          "border border-error bg-error text-white shadow-sm hover:bg-[#9c2f32]",
        outline:
          "border border-border bg-white text-text-primary shadow-[0_1px_2px_rgba(67,26,48,0.05)] hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700",
        secondary:
          "border border-transparent bg-bg-tertiary text-text-secondary hover:bg-primary-50 hover:text-primary-700",
        ghost: "text-text-secondary hover:bg-primary-50 hover:text-primary-700",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-11 rounded-lg px-6 text-[15px]",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export type ButtonVariantProps = VariantProps<typeof buttonVariants>
