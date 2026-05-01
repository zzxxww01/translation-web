import { cva, type VariantProps } from "class-variance-authority"

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:border disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-slate-950 text-white shadow-sm hover:bg-slate-800 active:bg-slate-900",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:
          "border border-slate-200 bg-white text-slate-900 shadow-none hover:border-slate-300 hover:bg-slate-50",
        secondary:
          "bg-slate-100 text-slate-900 shadow-none hover:bg-slate-200",
        ghost: "text-slate-700 hover:bg-slate-100 hover:text-slate-950",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2 max-sm:h-11",
        sm: "h-8 px-3 text-xs max-sm:h-10",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10 max-sm:h-11 max-sm:w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export type ButtonVariantProps = VariantProps<typeof buttonVariants>
