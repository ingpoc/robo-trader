import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/12 text-primary",
        secondary: "border-border bg-muted text-muted-foreground",
        tertiary: "border-transparent bg-transparent text-copper-700",
        outline: "border-border bg-card text-foreground",
        destructive: "border-destructive/20 bg-destructive/10 text-destructive",
        active: "border-emerald-200 bg-emerald-50 text-emerald-700",
        inactive: "border-border bg-muted text-muted-foreground",
        pending: "border-amber-200 bg-amber-50 text-amber-700",
        positive: "border-emerald-200 bg-emerald-50 text-emerald-700",
        negative: "border-rose-200 bg-rose-50 text-rose-700",
        neutral: "border-border bg-muted text-muted-foreground",
        success: "border-emerald-200 bg-emerald-50 text-emerald-700",
        warning: "border-amber-200 bg-amber-50 text-amber-700",
        error: "border-rose-200 bg-rose-50 text-rose-700",
        info: "border-copper-200 bg-copper-50 text-copper-700",
        buy: "border-emerald-200 bg-emerald-50 text-emerald-700",
        sell: "border-rose-200 bg-rose-50 text-rose-700",
        hold: "border-copper-200 bg-copper-50 text-copper-700",
        subtle: "border-transparent bg-muted/70 text-muted-foreground",
      },
      size: {
        xs: "px-2 py-0.5 text-[11px]",
        sm: "px-2.5 py-1 text-xs",
        md: "px-3 py-1 text-xs",
        lg: "px-3.5 py-1.5 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
