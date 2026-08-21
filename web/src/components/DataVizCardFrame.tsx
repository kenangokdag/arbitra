"use client";

import type { ReactNode } from "react";
import {
  Compass,
  Maximize2,
  ExternalLink,
  Download,
  Sparkles,
  Layers,
} from "lucide-react";
import type { Zone } from "@/lib/zone";
import { BRAND } from "@/lib/brand";

const ZONE_VIZ: Record<
  Zone,
  { label: string; color: string; bg: string; icon: typeof Compass }
> = {
  discovery: { label: "Keşif", color: "#D97706", bg: "#FEF3C7", icon: Compass },
  curation: { label: "Süzme & İnceleme", color: "#D97706", bg: "#FEF3C7", icon: Layers },
  gapatlas: { label: "Literatür Boşluğu", color: "#0E4F4A", bg: "#F0FDFA", icon: Layers },
  authoring: { label: "Yazım & Hazırlık", color: "#D97706", bg: "#FEF3C7", icon: Layers },
  defense: { label: "Savunma", color: "#C9A961", bg: "#FEF7E0", icon: Layers },
};

interface DataVizCardFrameProps {
  zone?: Zone;
  title: string;
  subtitle?: string;
  sourceBadge?: string;
  uniqueBadge?: boolean;
  children: ReactNode;
  legend?: ReactNode;
  controls?: ReactNode;
  onFullscreen?: () => void;
  onExport?: () => void;
  onOpenNew?: () => void;
  prominent?: boolean;
  customIcon?: typeof Compass;
}

export function DataVizCardFrame({
  zone = "curation",
  title,
  subtitle,
  sourceBadge,
  uniqueBadge = false,
  children,
  legend,
  controls,
  onFullscreen,
  onExport,
  onOpenNew,
  prominent = false,
  customIcon,
}: DataVizCardFrameProps) {
  const z = ZONE_VIZ[zone];
  const ZIcon = customIcon ?? z.icon;

  return (
    <div
      className="bg-white rounded-2xl overflow-hidden relative transition-all"
      style={{
        border: prominent ? `2px solid ${z.color}40` : "1px solid #E7E5E4",
        boxShadow: prominent
          ? `0 4px 20px -4px ${z.color}20, 0 1px 2px rgba(0,0,0,0.04)`
          : "0 1px 2px rgba(0,0,0,0.02)",
      }}
    >
      {/* Header */}
      <div className="px-5 md:px-6 py-4 border-b border-stone-100 flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
            style={{ background: `${z.color}15`, color: z.color }}
          >
            <ZIcon className="w-4 h-4" strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-crimson italic text-lg md:text-xl font-semibold text-stone-900 leading-tight">
                {title}
              </h3>
              {uniqueBadge && (
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold border inline-flex items-center gap-1"
                  style={{
                    background: `${z.color}15`,
                    color: z.color,
                    borderColor: `${z.color}40`,
                  }}
                >
                  <Sparkles className="w-2.5 h-2.5" strokeWidth={2.5} />
                  Sadece {BRAND}&#39;da
                </span>
              )}
            </div>
            {subtitle && (
              <p className="text-xs text-stone-500 mt-0.5 leading-relaxed">
                {subtitle}
              </p>
            )}
            {sourceBadge && (
              <span
                className={`inline-flex items-center gap-1.5 mt-2 px-2 py-0.5 rounded-md text-[11px] font-mono-pmid ${
                  prominent ? "font-semibold" : ""
                }`}
                style={{
                  background: prominent ? `${z.color}15` : "#F5F5F4",
                  color: prominent ? z.color : "#57534E",
                  border: `1px solid ${prominent ? `${z.color}30` : "#E7E5E4"}`,
                }}
              >
                <span
                  className="w-1 h-1 rounded-full"
                  style={{ background: prominent ? z.color : "#A8A29E" }}
                />
                {sourceBadge}
              </span>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={onFullscreen}
            title="Tam ekran"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100 hover:text-stone-700 transition-colors"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onOpenNew}
            title="Yeni sekmede aç"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100 hover:text-stone-700 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onExport}
            title="Dışa aktar"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100 hover:text-stone-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Visualization area */}
      <div className="relative bg-stone-50/40">{children}</div>

      {/* Legend / controls footer */}
      {(legend || controls) && (
        <div className="px-5 md:px-6 py-3 border-t border-stone-100 bg-white flex items-center justify-between flex-wrap gap-3">
          {legend && (
            <div className="flex items-center gap-4 flex-wrap">{legend}</div>
          )}
          {controls && (
            <div className="flex items-center gap-2 flex-wrap">{controls}</div>
          )}
        </div>
      )}
    </div>
  );
}
