import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const labelVariants = cva(
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
  {
    variants: {
      variant: {
        default: "text-warmgray-900 dark:text-warmgray-100",
        error: "text-rose-600 dark:text-rose-400",
        success: "text-emerald-600 dark:text-emerald-400",
        info: "text-copper-600 dark:text-copper-400",
      },
      required: {
        true: "after:content-['*'] after:ml-1 after:text-rose-500",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      required: false,
    },
  }
)

export interface LabelProps
  extends React.LabelHTMLAttributes<HTMLLabelElement>,
    VariantProps<typeof labelVariants> {}

const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, variant, required, ...props }, ref) => (
    <label
      ref={ref}
      className={cn(labelVariants({ variant, required }), className)}
      {...props}
    />
  )
)

Label.displayName = "Label"

export { Label }
