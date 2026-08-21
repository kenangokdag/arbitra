"use client";

import { Check, GraduationCap } from "lucide-react";
import { workbenches } from "@/lib/nav-config";

type NodeState = "done" | "active" | "locked" | "pending";

const TOTAL_STEPS = workbenches.reduce((acc, wb) => acc + wb.pages.length, 0);

function deriveProgress(currentPageId: string) {
  let cumulative = 0;
  let activeWbId: string | null = null;
  for (const wb of workbenches) {
    const idx = wb.pages.findIndex((p) => p.id === currentPageId);
    if (idx >= 0) {
      activeWbId = wb.id;
      cumulative += idx;
      return { completed: cumulative, activeWbId };
    }
    cumulative += wb.pages.length;
  }
  return { completed: 0, activeWbId };
}

function nodeState(wbId: string, activeWbId: string | null): NodeState {
  if (!activeWbId) return "locked";
  const idx = workbenches.findIndex((w) => w.id === wbId);
  const activeIdx = workbenches.findIndex((w) => w.id === activeWbId);
  if (idx < activeIdx) return "done";
  if (idx === activeIdx) return "active";
  return "locked";
}

export function CompassRoute({ currentPageId }: { currentPageId: string }) {
  const { completed, activeWbId } = deriveProgress(currentPageId);

  return (
    <div className="overflow-x-auto py-6">
      <style>{`
        @keyframes pmNodeGlow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(79,70,229,0.45); }
          50%      { box-shadow: 0 0 0 6px rgba(79,70,229,0); }
        }
        @keyframes pmDotPulse {
          0%, 100% { opacity: 0.55; transform: scale(0.85); }
          50%      { opacity: 1; transform: scale(1.1); }
        }
        @keyframes pmGradGlow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(201,169,97,0.4); }
          50%      { box-shadow: 0 0 0 8px rgba(201,169,97,0); }
        }
      `}</style>

      <div className="mx-auto flex min-w-[760px] items-center gap-2 px-4">
        {workbenches.map((wb, i) => {
          const state = nodeState(wb.id, activeWbId);
          const WbIcon = wb.icon;
          const baseStyle: React.CSSProperties = {};

          let circle: React.CSSProperties = {
            border: "2px solid var(--color-rule)",
            background: "white",
            color: wb.color,
          };
          let icon: React.ReactNode = (
            <WbIcon className="h-5 w-5" strokeWidth={2} />
          );

          if (state === "done") {
            circle = { background: wb.color, border: `2px solid ${wb.color}`, color: "white" };
            icon = <Check className="h-5 w-5" strokeWidth={3} />;
          } else if (state === "active") {
            circle = {
              background: "white",
              border: "2px solid var(--color-accent)",
              color: "var(--color-accent)",
              animation: "pmNodeGlow 1.6s ease-in-out infinite",
            };
          } else if (state === "locked") {
            circle = {
              background: "var(--color-bg-soft)",
              border: "2px solid var(--color-rule-soft)",
              color: "var(--color-ink-faint)",
              opacity: 0.55,
              cursor: "not-allowed",
            };
          }

          const subDotStyle: React.CSSProperties =
            state === "done"
              ? { background: "var(--color-accent)", border: "1px solid var(--color-accent)" }
              : state === "active"
                ? {
                    background: "var(--color-accent)",
                    animation: "pmDotPulse 1.4s ease-in-out infinite",
                  }
                : { background: "transparent", border: "1px solid var(--color-rule)", opacity: 0.35 };

          return (
            <div key={wb.id} className="flex flex-1 items-center" style={baseStyle}>
              <div
                className="relative flex flex-col items-center"
                title={`${wb.label} (${wb.pages.length} sayfa)`}
              >
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-full transition-all"
                  style={circle}
                >
                  {icon}
                </div>
                <span
                  aria-hidden="true"
                  className="mt-2 block h-1.5 w-1.5 rounded-full"
                  style={subDotStyle}
                />
                <span
                  className="mt-1.5 max-w-[88px] truncate text-center font-mono text-[10px]"
                  style={{
                    color: state === "locked" ? "var(--color-ink-faint)" : "var(--color-ink-mute)",
                  }}
                >
                  {wb.label}
                </span>
              </div>
              {i < workbenches.length - 1 && (
                <div
                  className="mx-2 h-0.5 flex-1"
                  style={{
                    background:
                      state === "done"
                        ? "var(--color-accent)"
                        : state === "active"
                          ? "linear-gradient(to right, var(--color-accent) 50%, var(--color-rule-soft) 50%)"
                          : "var(--color-rule-soft)",
                  }}
                />
              )}
            </div>
          );
        })}

        {/* Graduation node */}
        <div className="flex flex-col items-center">
          <div
            className="flex h-11 w-11 items-center justify-center rounded-full text-xl"
            style={
              completed >= TOTAL_STEPS - 1
                ? {
                    background: "#FEF3C7",
                    border: "2px solid #C9A961",
                    color: "#92400E",
                    animation: "pmGradGlow 2s ease-in-out infinite",
                  }
                : {
                    border: "2px dashed var(--color-rule)",
                    background: "var(--color-bg-soft)",
                    color: "var(--color-ink-faint)",
                  }
            }
          >
            <GraduationCap className="h-5 w-5" strokeWidth={2} />
          </div>
          <span
            className="mt-1.5 max-w-[88px] truncate text-center font-mono text-[10px]"
            style={{
              color:
                completed >= TOTAL_STEPS - 1
                  ? "#92400E"
                  : "var(--color-ink-faint)",
            }}
          >
            {completed >= TOTAL_STEPS - 1 ? "Tebrikler!" : "Mezuniyet"}
          </span>
        </div>
      </div>

      <div className="mx-auto mt-4 max-w-[760px] px-4">
        <div
          className="font-mono text-[11px]"
          style={{ color: "var(--color-ink-mute)" }}
        >
          {completed} / {TOTAL_STEPS} adim tamamlandi
        </div>
      </div>
    </div>
  );
}
