const LABELS: Record<string, string> = { d: "D", w: "W", s: "S", t: "T" };

export function EstraBars({
  scores,
  size = "sm",
}: {
  scores: { d: number; w: number; s: number; t: number };
  size?: "sm" | "md";
}) {
  return (
    <div className="flex items-end gap-0.5">
      {Object.entries(scores).map(([key, val]) => {
        const intensity = val / 100;
        return (
          <div key={key} className="flex flex-col items-center gap-0.5" title={`${LABELS[key]}: ${val}`}>
            <div
              className={`${size === "sm" ? "w-1.5" : "w-2"} relative overflow-hidden rounded-sm`}
              style={{
                height: size === "sm" ? 16 : 24,
                background: "rgba(79, 70, 229, 0.15)",
              }}
            >
              <div
                className="absolute bottom-0 left-0 right-0 rounded-sm"
                style={{
                  height: `${intensity * 100}%`,
                  background: `linear-gradient(180deg, #7C3AED ${100 - intensity * 100}%, #4F46E5 100%)`,
                }}
              />
            </div>
            <span className="font-mono text-[9px] text-stone-400">{LABELS[key]}</span>
          </div>
        );
      })}
    </div>
  );
}
