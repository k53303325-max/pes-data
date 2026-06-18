import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, ...props }, ref) => {
    const variants = {
      primary:
        "bg-brand-purple hover:bg-brand-accent text-white shadow-lg shadow-brand-purple/25",
      secondary: "bg-white/10 hover:bg-white/15 text-white border border-white/10",
      ghost: "hover:bg-white/10 text-white/80 hover:text-white",
      outline:
        "border border-brand-purple text-brand-purple hover:bg-brand-purple/10",
    };

    const sizes = {
      sm: "px-3 py-1.5 text-sm rounded-lg",
      md: "px-5 py-2.5 text-sm rounded-xl",
      lg: "px-8 py-3.5 text-base rounded-xl font-semibold",
    };

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
