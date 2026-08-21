import { Maximize2, Download } from "lucide-react";

export function DataVizCard({
  title,
  subtitle,
  badge,
  zoneTint = "#E8A157",
  children,
}: {
  title: string;
  subtitle?: string;
  badge?: string;
  zoneTint?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="overflow-hidden rounded-2xl border border-stone-200 bg-white"
      style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
    >
      <div className="flex items-center justify-between border-b border-stone-100 px-5 py-3">
        <div>
          <h3 className="font-display text-base font-semibold text-stone-900">{title}</h3>
          <div className="mt-0.5 flex items-center gap-2">
            {subtitle && <span className="text-xs text-stone-500">{subtitle}</span>}
            {badge && (
              <span
                className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  background: `${zoneTint}15`,
                  color: zoneTint,
                  border: `1px solid ${zoneTint}30`,
                }}
              >
                {badge}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-400 hover:bg-stone-50 hover:text-stone-600">
            <Maximize2 className="h-4 w-4" />
          </button>
          <button className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-400 hover:bg-stone-50 hover:text-stone-600">
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}
