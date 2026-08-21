import { forwardRef, type ButtonHTMLAttributes, type CSSProperties } from "react";

type Variant = "ritual" | "secondary" | "ghost" | "adviser";
type Size = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-10 px-4 text-[14px]",
  lg: "h-12 px-5 text-[15px]",
};

const radiusClasses: Record<Size, string> = {
  sm: "rounded-[6px]",
  md: "rounded-[8px]",
  lg: "rounded-[10px]",
};

function PenNibIcon({ style }: { style?: CSSProperties }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
      aria-hidden="true"
    >
      <path d="M14 2L7 13l4 4 11-7-8-8z" />
      <path d="M7 13l-4 8 8-4" />
      <path d="M11 17L7 13" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className="animate-spin"
      aria-hidden="true"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

const variantConfig: Record<
  Variant,
  {
    className: string;
    style: CSSProperties;
    hoverStyle?: Record<string, string>;
  }
> = {
  ritual: {
    className: "font-display font-semibold",
    style: {
      background: "#E8A157",
      border: "1px solid #E8A157",
      color: "var(--color-ink)",
      boxShadow: "0 1px 3px rgba(232,161,87,0.25)",
    },
    hoverStyle: { background: "#D4923E", borderColor: "#D4923E" },
  },
  secondary: {
    className: "font-medium",
    style: {
      background: "var(--color-bg-card)",
      border: "1px solid var(--color-rule)",
      color: "var(--color-ink-soft)",
      boxShadow: "0 1px 2px rgba(15,23,42,0.04)",
    },
    hoverStyle: {
      background: "var(--color-bg-soft)",
      borderColor: "var(--color-ink-soft)",
    },
  },
  ghost: {
    className: "font-medium",
    style: {
      background: "transparent",
      border: "1px solid transparent",
      color: "var(--color-ink-mute)",
    },
    hoverStyle: {
      background: "var(--color-accent-pale)",
      color: "var(--color-ink)",
    },
  },
  adviser: {
    className: "font-display italic",
    style: {
      background: "var(--color-accent-pale)",
      border: "1px solid rgba(79,70,229,0.22)",
      color: "#312E81",
    },
    hoverStyle: { background: "#C7D2FE" },
  },
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "ritual",
      size = "md",
      isLoading = false,
      disabled,
      className = "",
      children,
      onMouseEnter,
      onMouseLeave,
      style: styleProp,
      ...props
    },
    ref,
  ) => {
    const cfg = variantConfig[variant];
    const radius = variant === "adviser" ? "rounded-full" : radiusClasses[size];

    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`inline-flex items-center justify-center gap-1.5 tracking-[-0.005em] transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${sizeClasses[size]} ${radius} ${cfg.className} ${className}`}
        style={{ ...cfg.style, ...styleProp }}
        onMouseEnter={(event) => {
          if (!isDisabled && cfg.hoverStyle) {
            Object.assign(event.currentTarget.style, cfg.hoverStyle);
          }
          onMouseEnter?.(event);
        }}
        onMouseLeave={(event) => {
          if (!isDisabled) {
            Object.assign(event.currentTarget.style, cfg.style);
            if (styleProp) {
              Object.assign(event.currentTarget.style, styleProp);
            }
          }
          onMouseLeave?.(event);
        }}
        {...props}
      >
        {isLoading ? <Spinner /> : null}
        {variant === "adviser" && !isLoading ? (
          <PenNibIcon style={{ color: "var(--color-accent)" }} />
        ) : null}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
