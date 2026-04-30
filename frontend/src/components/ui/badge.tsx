import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[var(--color-near-black)] text-[var(--color-white)]",
        secondary:
          "border-transparent bg-[var(--color-near-black)]/10 text-[var(--color-near-black)]",
        outline:
          "border-[var(--color-near-black)]/20 text-[var(--color-near-black)]",
        keeper:
          "border-transparent bg-[var(--color-gold)]/20 text-[var(--color-gold-dark)]",
        seller:
          "border-transparent bg-[var(--color-near-black)]/5 text-[var(--color-muted)]",
        unranked:
          "border-[var(--color-near-black)]/10 text-[var(--color-muted)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge };
