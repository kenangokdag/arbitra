import { Layers } from "lucide-react";

export function PlaceholderPage({
  title,
  workbenchLabel,
  color = "#94A3B8",
}: {
  title: string;
  workbenchLabel?: string;
  color?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center px-6"
      style={{ height: "calc(100vh - 60px)" }}
    >
      <div
        className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl"
        style={{ background: `${color}15`, color }}
      >
        <Layers className="h-8 w-8" strokeWidth={1.5} />
      </div>
      {workbenchLabel && (
        <div className="mb-2 font-mono text-xs uppercase tracking-widest" style={{ color }}>
          {workbenchLabel}
        </div>
      )}
      <h2 className="font-display mb-2 text-center text-3xl font-semibold italic text-stone-900">{title}</h2>
      <p className="max-w-md text-center text-sm leading-relaxed text-stone-500">
        Bu sayfa yakinda tasarlanacak. Tezgah akisinin bir parcasi olarak gelecek hafta yayinda olacak.
      </p>
      <div className="mt-6 flex items-center gap-2 text-xs text-stone-400">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-stone-300" />
        <span>Gelistirme asamasinda</span>
      </div>
    </div>
  );
}
