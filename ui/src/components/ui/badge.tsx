import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-warmgray-900",
  {
    variants: {
      variant: {
        // Default - Primary copper
        default: "bg-copper-100 dark:bg-copper-950 text-copper-900 dark:text-copper-100 border border-copper-300 dark:border-copper-700 shadow-sm",
        
        // Status variants
        active: "bg-emerald-100 dark:bg-emerald-950 text-emerald-900 dark:text-emerald-100 border border-emerald-300 dark:border-emerald-700",
        inactive: "bg-warmgray-100 dark:bg-warmgray-800 text-warmgray-700 dark:text-warmgray-300 border border-warmgray-300 dark:border-warmgray-600",
        pending: "bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-100 border border-amber-300 dark:border-amber-700",
        
        // Sentiment variants
        positive: "bg-emerald-100 dark:bg-emerald-950 text-emerald-900 dark:text-emerald-100 border border-emerald-300 dark:border-emerald-700 shadow-sm shadow-emerald-200 dark:shadow-emerald-900",
        negative: "bg-rose-100 dark:bg-rose-950 text-rose-900 dark:text-rose-100 border border-rose-300 dark:border-rose-700 shadow-sm shadow-rose-200 dark:shadow-rose-900",
        neutral: "bg-warmgray-100 dark:bg-warmgray-800 text-warmgray-700 dark:text-warmgray-300 border border-warmgray-300 dark:border-warmgray-600",
        
        // Action variants
        success: "bg-emerald-100 dark:bg-emerald-950 text-emerald-900 dark:text-emerald-100 border border-emerald-300 dark:border-emerald-700 shadow-sm",
        warning: "bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-100 border border-amber-300 dark:border-amber-700 shadow-sm",
        error: "bg-rose-100 dark:bg-rose-950 text-rose-900 dark:text-rose-100 border border-rose-300 dark:border-rose-700 shadow-sm",
        info: "bg-copper-100 dark:bg-copper-950 text-copper-900 dark:text-copper-100 border border-copper-300 dark:border-copper-700 shadow-sm",
        
        // Trading specific
        buy: "bg-emerald-100 dark:bg-emerald-950 text-emerald-900 dark:text-emerald-100 border border-emerald-300 dark:border-emerald-700 font-bold shadow-md shadow-emerald-200 dark:shadow-emerald-900",
        sell: "bg-rose-100 dark:bg-rose-950 text-rose-900 dark:text-rose-100 border border-rose-300 dark:border-rose-700 font-bold shadow-md shadow-rose-200 dark:shadow-rose-900",
        hold: "bg-copper-100 dark:bg-copper-950 text-copper-900 dark:text-copper-100 border border-copper-300 dark:border-copper-700 font-bold shadow-md shadow-copper-200 dark:shadow-copper-900",
        
        // Secondary - Light background
        secondary: "bg-warmgray-50 dark:bg-warmgray-900 text-warmgray-700 dark:text-warmgray-300 border border-warmgray-200 dark:border-warmgray-700",
        
        // Outline - Minimal
        outline: "bg-transparent text-copper-600 dark:text-copper-400 border border-copper-300 dark:border-copper-600",
        
        // Subtle - Very light
        subtle: "bg-warmgray-100 dark:bg-warmgray-800 text-warmgray-600 dark:text-warmgray-400 border border-transparent",
      },
      size: {
        xs: "px-2 py-0.5 text-xs",
        sm: "px-2.5 py-1 text-xs",
        md: "px-3 py-1.5 text-sm",
        lg: "px-4 py-2 text-base",
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
