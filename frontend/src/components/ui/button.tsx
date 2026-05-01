import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-all cursor-pointer disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terracotta",
  {
    variants: {
      variant: {
        default:
          "bg-near-black text-white hover:bg-near-black/90",
        ghost:
          "bg-transparent hover:bg-near-black/5",
        outline:
          "border border-near-black/20 bg-transparent hover:border-terracotta hover:text-terracotta",
        terracotta:
          "bg-terracotta text-white hover:bg-terracotta/80",
        cobalt:
          "bg-cobalt text-white hover:bg-cobalt/80",
      },
      size: {
        default: "h-10 px-5 py-2 rounded-sm",
        sm: "h-8 px-3 rounded-sm text-xs",
        lg: "h-12 px-8 rounded-sm",
        icon: "h-10 w-10 rounded-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
