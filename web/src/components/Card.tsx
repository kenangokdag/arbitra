import { cn } from "@/lib/cn";

export function Card({
  children,
  className,
  title,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-[10px] border border-rule bg-bg-card p-[18px_20px] shadow-sm transition-shadow duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:shadow-md",
        className
      )}
    >
      {title ? <h3 className="serif mb-2.5 text-[16px] font-medium italic">{title}</h3> : null}
      {children}
    </section>
  );
}

export function CardRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-3">
      {children}
    </div>
  );
}
