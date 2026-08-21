"use client";

import React, { useState } from "react";
import {
  Compass,
  Library,
  Map,
  PenTool,
  Shield,
  Check,
  Copy,
  Sparkles,
  ArrowRight,
  FileText,
  Folder,
  Bell,
  Settings,
  Crown,
  AlertCircle,
  type LucideIcon,
} from "lucide-react";
import { BRAND } from "@/lib/brand";

// ============================================================
// PAPERMIND DESIGN TOKENS — D2
// ============================================================

interface SemanticColor {
  DEFAULT: string;
  soft: string;
  border: string;
  text: string;
}

interface ZoneConfig {
  label: string;
  icon: LucideIcon;
  pages: string;
  desc: string;
  meaning: string;
  color: string;
  soft: string;
  border: string;
  text: string;
}

const TOKENS = {
  base: {
    bg: "#FAFAF9",
    surface: "#FFFFFF",
    surfaceMuted: "#F5F5F4",
    border: "#E7E5E4",
    borderStrong: "#D6D3D1",
    text: "#1C1917",
    textBody: "#44403C",
    textMuted: "#78716C",
    textSubtle: "#A8A29E",
  },
  brand: {
    gradientFrom: "#4F46E5",
    gradientTo: "#7C3AED",
    primary: "#4F46E5",
    primarySoft: "#EEF2FF",
    primaryBorder: "#E0E7FF",
  },
  accent: {
    DEFAULT: "#D97706",
    soft: "#FEF3C7",
    border: "#FDE68A",
    text: "#92400E",
  },
  semantic: {
    success: { DEFAULT: "#10B981", soft: "#D1FAE5", border: "#A7F3D0", text: "#065F46" },
    warning: { DEFAULT: "#F59E0B", soft: "#FEF3C7", border: "#FDE68A", text: "#92400E" },
    error: { DEFAULT: "#EF4444", soft: "#FEE2E2", border: "#FECACA", text: "#991B1B" },
    info: { DEFAULT: "#0EA5E9", soft: "#E0F2FE", border: "#BAE6FD", text: "#075985" },
  } satisfies Record<string, SemanticColor>,
  zones: {
    discovery: {
      label: "Kesif",
      icon: Compass,
      pages: "1.1 – 1.5",
      desc: "Konu belirleme, bibliyometrik & tematik analiz",
      meaning: "Sakin, analitik acilis. Renksizlik = tarafsiz bakis. Henuz yargi yok, yalnizca gozlem.",
      color: "#475569",
      soft: "#F1F5F9",
      border: "#CBD5E1",
      text: "#1E293B",
    },
    curation: {
      label: "Suzme & Inceleme",
      icon: Library,
      pages: "2.1 – 2.5",
      desc: "Literatur onerileri, sentez, kalite suzme",
      meaning: "Marka ailesi. Suzme bir yargi eylemidir — markanin gerceklestigi an.",
      color: "#7C3AED",
      soft: "#F5F3FF",
      border: "#DDD6FE",
      text: "#5B21B6",
    },
    gapAtlas: {
      label: "Literatur Boslugu",
      icon: Map,
      pages: "3.1 – 3.5",
      desc: "Bosluk haritasi, profil, ozgunluk",
      meaning: "Kartograf serinligi. Killer feature — digerlerinden ayrisma dogru.",
      color: "#0F766E",
      soft: "#F0FDFA",
      border: "#99F6E4",
      text: "#115E59",
    },
    authoring: {
      label: "Yazim & Hazirlik",
      icon: PenTool,
      pages: "4.1 – 4.4",
      desc: "Taslak, dil, atif, format",
      meaning: "Murekkep. Bos sayfa hissi — yazi sayfayi doldurur, renk degil.",
      color: "#292524",
      soft: "#F5F5F4",
      border: "#D6D3D1",
      text: "#1C1917",
    },
    defense: {
      label: "Savunma",
      icon: Shield,
      pages: "5.1 – 5.6",
      desc: "Juri & hakem simulasyonu",
      meaning: "Ciddiyet ve hafif gerilim. Kursu ani — gold degil, cunku gold zafer hissi verir.",
      color: "#881337",
      soft: "#FFF1F2",
      border: "#FECDD3",
      text: "#881337",
    },
  } satisfies Record<string, ZoneConfig>,
};

type ZoneKey = keyof typeof TOKENS.zones;

// ============================================================
// HELPERS
// ============================================================

function SectionLabel({ children, color = "#4F46E5" }: { children: React.ReactNode; color?: string }) {
  return (
    <div
      className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border"
      style={{ background: `${color}10`, color, borderColor: `${color}25` }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {children}
    </div>
  );
}

function ColorChip({ name, value }: { name: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard?.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const c = value.replace("#", "");
  const r = parseInt(c.substr(0, 2), 16);
  const g = parseInt(c.substr(2, 2), 16);
  const b = parseInt(c.substr(4, 2), 16);
  const luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  const textColor = luma < 0.6 ? "#FFFFFF" : "#1C1917";

  return (
    <button
      onClick={handleCopy}
      className="group relative rounded-xl overflow-hidden transition-all hover:scale-[1.02] active:scale-[0.99] text-left h-20 border border-stone-200"
      style={{ background: value }}
    >
      <div className="p-3 h-full flex flex-col justify-between" style={{ color: textColor }}>
        <div className="text-[10px] font-mono opacity-70 truncate">{name}</div>
        <div className="font-mono text-[11px] font-semibold">{value.toUpperCase()}</div>
      </div>
      <div
        className={`absolute top-1.5 right-1.5 w-5 h-5 rounded flex items-center justify-center transition-all ${
          copied ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        }`}
        style={{ background: "rgba(255,255,255,0.95)", color: "#1C1917" }}
      >
        {copied ? <Check className="w-2.5 h-2.5" strokeWidth={3} /> : <Copy className="w-2.5 h-2.5" />}
      </div>
    </button>
  );
}

// ============================================================
// CANLI SAYFA SNAPSHOT
// ============================================================

function DemoSnapshot({ zoneKey }: { zoneKey: ZoneKey }) {
  const zone = TOKENS.zones[zoneKey];
  const Icon = zone.icon;

  const titles: Record<string, string> = {
    discovery: "Bibliyometrik Analiz",
    curation: "Onerilen Literatur",
    gapAtlas: "Bosluk Haritasi",
    authoring: "Makale Taslagi",
    defense: "Juri Simulasyonu",
  };

  return (
    <div className="rounded-2xl bg-stone-50 p-6 border border-stone-200 overflow-hidden">
      {/* TopNav */}
      <div className="flex items-center justify-between pb-3 border-b border-stone-200 mb-5">
        <div className="flex items-center gap-3">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center text-white text-xs font-display italic font-bold"
            style={{ background: `linear-gradient(135deg, ${TOKENS.brand.gradientFrom}, ${TOKENS.brand.gradientTo})` }}
          >
            {BRAND[0]}
          </div>
          <span className="font-display italic font-semibold text-stone-900">{BRAND}</span>
          <span className="text-xs text-stone-300">/</span>
          <span className="text-xs text-stone-500">{zone.pages}</span>
          <span className="text-xs text-stone-300">/</span>
          <span className="text-xs text-stone-900 font-medium">{zone.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <Bell className="w-3.5 h-3.5 text-stone-400" />
          <Settings className="w-3.5 h-3.5 text-stone-400" />
        </div>
      </div>

      {/* PageHeader */}
      <div className="mb-5">
        <SectionLabel color={zone.color}>{zone.label} · {zone.pages}</SectionLabel>
        <h3 className="font-display italic text-2xl font-semibold text-stone-900 mt-2.5 mb-1.5 leading-tight">
          {titles[zoneKey]}
        </h3>
        <p className="text-sm text-stone-600">{zone.desc}</p>
      </div>

      {/* Stat kartlari */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[
          { label: "Toplam", value: "1.847", StatIcon: FileText },
          { label: "Aktif", value: "312", StatIcon: Folder },
          { label: "Yeni", value: "+47", StatIcon: Sparkles },
        ].map((s) => (
          <div key={s.label} className="bg-white border border-stone-200 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <div
                className="w-7 h-7 rounded-md flex items-center justify-center"
                style={{ background: zone.soft, color: zone.color }}
              >
                <s.StatIcon className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="font-display italic text-xl font-semibold text-stone-900">{s.value}</div>
            <div className="text-xs text-stone-500">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Buton satiri */}
      <div className="flex items-center gap-2 pt-4 border-t border-stone-100">
        <button
          className="flex items-center gap-1.5 text-white px-3.5 py-2 rounded-lg text-xs font-medium"
          style={{
            background: `linear-gradient(135deg, ${TOKENS.brand.gradientFrom}, ${TOKENS.brand.gradientTo})`,
            boxShadow: `0 2px 8px -2px ${TOKENS.brand.gradientFrom}40`,
          }}
        >
          <Sparkles className="w-3 h-3" />
          Birincil eylem
        </button>
        <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium border border-stone-300 bg-white text-stone-800">
          Ikincil
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// ============================================================
// AMBER KULLANIM ORNEKLERI
// ============================================================

function AccentUsageExamples() {
  return (
    <div className="grid md:grid-cols-3 gap-3">
      {/* Pro rozeti */}
      <div className="bg-white border border-stone-200 rounded-xl p-5">
        <div className="text-[10px] font-mono uppercase tracking-widest text-stone-500 mb-3">
          Pro rozeti
        </div>
        <div className="flex items-center justify-between mb-3">
          <span className="font-display italic text-base font-semibold text-stone-900">
            Juri simulasyonu
          </span>
          <span
            className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold rounded-md text-white"
            style={{ background: "linear-gradient(135deg, #D97706 0%, #B45309 100%)" }}
          >
            <Crown className="w-2.5 h-2.5" strokeWidth={2.5} />
            PRO
          </span>
        </div>
        <p className="text-xs text-stone-500 leading-relaxed">
          Ucretli ozellikler. Amber = sicak, davetkar ama sinirli.
        </p>
      </div>

      {/* Hint banner */}
      <div className="bg-white border border-stone-200 rounded-xl p-5">
        <div className="text-[10px] font-mono uppercase tracking-widest text-stone-500 mb-3">
          Bilgi banner&apos;i
        </div>
        <div
          className="flex items-start gap-2 rounded-lg p-2.5 mb-3"
          style={{ background: TOKENS.accent.soft, borderLeft: `3px solid ${TOKENS.accent.DEFAULT}` }}
        >
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: TOKENS.accent.text }} />
          <div className="text-xs leading-relaxed" style={{ color: TOKENS.accent.text }}>
            Bu analiz son 10 yili kapsiyor.
          </div>
        </div>
        <p className="text-xs text-stone-500 leading-relaxed">
          Dikkat cekici ama agresif degil. Sayfada en fazla bir tane.
        </p>
      </div>

      {/* Danisman */}
      <div className="bg-white border border-stone-200 rounded-xl p-5">
        <div className="text-[10px] font-mono uppercase tracking-widest text-stone-500 mb-3">
          Danisman vurgusu
        </div>
        <button
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border mb-3"
          style={{
            background: TOKENS.accent.soft,
            color: TOKENS.accent.text,
            borderColor: TOKENS.accent.border,
          }}
        >
          <Sparkles className="w-3 h-3" />
          Danismana sor
        </button>
        <p className="text-xs text-stone-500 leading-relaxed">
          Sicak insan dokunusu. Soguk veri arasinda bir ada.
        </p>
      </div>
    </div>
  );
}

// ============================================================
// ANA SAYFA
// ============================================================

export function ColorTokensPage() {
  const [activeZone, setActiveZone] = useState<ZoneKey>("discovery");

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      {/* HEADER */}
      <header className="border-b border-stone-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="font-mono text-[10px] uppercase tracking-widest text-stone-500">
                  Design System · Internal Doc
                </span>
                <span className="text-stone-300">/</span>
                <span className="font-mono text-[10px] text-stone-700">D2</span>
              </div>
              <h1 className="font-display text-4xl md:text-5xl italic font-semibold leading-tight mb-2">
                Color Tokens
              </h1>
              <p className="text-stone-600 max-w-xl leading-relaxed">
                Tek zemin, bilincli renk dili. Her ton bir anlam tasir — ne arka plani boyar, ne de markayi ezer.
              </p>
            </div>
            <div className="text-right">
              <div className="text-[10px] font-mono uppercase tracking-widest text-stone-400 mb-1">
                Last updated
              </div>
              <div className="text-sm font-mono text-stone-700">2026.05.01</div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* SECTION 01 — BASE */}
        <section className="mb-16">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="font-mono text-xs text-stone-400">01</span>
            <h2 className="font-display italic text-2xl font-semibold">Base</h2>
          </div>
          <p className="text-sm text-stone-500 mb-6 ml-8">
            Tum sayfalarda degismeyen zemin, yuzey, kenarlik ve metin renkleri
          </p>

          <div className="grid grid-cols-3 md:grid-cols-5 gap-2 mb-3">
            <ColorChip name="base.bg" value={TOKENS.base.bg} />
            <ColorChip name="base.surface" value={TOKENS.base.surface} />
            <ColorChip name="base.surface-muted" value={TOKENS.base.surfaceMuted} />
            <ColorChip name="base.border" value={TOKENS.base.border} />
            <ColorChip name="base.border-strong" value={TOKENS.base.borderStrong} />
          </div>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
            <ColorChip name="base.text" value={TOKENS.base.text} />
            <ColorChip name="base.text-body" value={TOKENS.base.textBody} />
            <ColorChip name="base.text-muted" value={TOKENS.base.textMuted} />
            <ColorChip name="base.text-subtle" value={TOKENS.base.textSubtle} />
          </div>
        </section>

        {/* SECTION 02 — BRAND */}
        <section className="mb-16">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="font-mono text-xs text-stone-400">02</span>
            <h2 className="font-display italic text-2xl font-semibold">Brand</h2>
          </div>
          <p className="text-sm text-stone-500 mb-6 ml-8">
            Indigo→violet gradient — birincil eylemler ve marka kimligi. Her tezgahta aynidir.
          </p>

          <div className="grid md:grid-cols-3 gap-3">
            <div
              className="rounded-xl p-5 text-white relative overflow-hidden h-28 flex flex-col justify-between border border-stone-200"
              style={{
                background: `linear-gradient(135deg, ${TOKENS.brand.gradientFrom} 0%, ${TOKENS.brand.gradientTo} 100%)`,
              }}
            >
              <div className="text-[10px] font-mono uppercase tracking-widest opacity-80">brand.gradient</div>
              <div>
                <div className="font-display italic text-lg font-semibold">Primary</div>
                <div className="font-mono text-[10px] opacity-90 mt-0.5">
                  {TOKENS.brand.gradientFrom} → {TOKENS.brand.gradientTo}
                </div>
              </div>
            </div>
            <ColorChip name="brand.primary" value={TOKENS.brand.primary} />
            <ColorChip name="brand.primary-soft" value={TOKENS.brand.primarySoft} />
          </div>
        </section>

        {/* SECTION 03 — ACCENT (KISITLI) */}
        <section className="mb-16">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="font-mono text-xs text-stone-400">03</span>
            <h2 className="font-display italic text-2xl font-semibold">Accent</h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold ml-2" style={{ background: "#FEE2E2", color: "#991B1B" }}>
              KISITLI
            </span>
          </div>
          <p className="text-sm text-stone-500 mb-6 ml-8 max-w-2xl">
            Amber — yalnizca <span className="font-medium text-stone-900">danisman vurgusu, Pro rozeti, hint banner&apos;i </span>
            icin. Tezgah rengi degildir, dekoratif degildir. Sayfada en fazla bir-iki yerde.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-6">
            <ColorChip name="accent.DEFAULT" value={TOKENS.accent.DEFAULT} />
            <ColorChip name="accent.soft" value={TOKENS.accent.soft} />
            <ColorChip name="accent.border" value={TOKENS.accent.border} />
            <ColorChip name="accent.text" value={TOKENS.accent.text} />
          </div>

          <div className="ml-8 mb-3">
            <div className="text-[10px] font-mono uppercase tracking-widest text-stone-500 mb-3">
              Dogru kullanim — sayfa basina en fazla bir-iki nokta
            </div>
          </div>
          <AccentUsageExamples />
        </section>

        {/* SECTION 04 — ZONE ACCENTS */}
        <section className="mb-16">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="font-mono text-xs text-stone-400">04</span>
            <h2 className="font-display italic text-2xl font-semibold">Zone Accents</h2>
          </div>
          <p className="text-sm text-stone-500 mb-6 ml-8 max-w-2xl">
            Bes tezgahin kimlik rengi. Her renk bir <span className="font-medium text-stone-900">anlam</span> tasir —
            kabaca atanmis degil, tezgahin isiyle uyumlu.
          </p>

          {/* Anlam tablosu */}
          <div className="ml-8 mb-6 bg-white border border-stone-200 rounded-xl overflow-hidden">
            {(Object.entries(TOKENS.zones) as [ZoneKey, typeof TOKENS.zones[ZoneKey]][]).map(([key, z], i) => {
              const ZIcon = z.icon;
              return (
                <div
                  key={key}
                  className={`flex items-start gap-4 p-5 ${
                    i !== Object.keys(TOKENS.zones).length - 1 ? "border-b border-stone-100" : ""
                  }`}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: z.soft, color: z.color }}
                  >
                    <ZIcon className="w-4 h-4" strokeWidth={2} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 mb-1 flex-wrap">
                      <span className="font-display italic text-base font-semibold text-stone-900">{z.label}</span>
                      <span className="font-mono text-[10px] text-stone-400">{z.pages}</span>
                      <span className="font-mono text-[10px] text-stone-300">·</span>
                      <span className="font-mono text-[10px]" style={{ color: z.color }}>{z.color}</span>
                    </div>
                    <p className="text-sm text-stone-600 leading-relaxed">{z.meaning}</p>
                  </div>
                  <div className="flex-shrink-0 hidden md:block">
                    <div
                      className="w-16 h-16 rounded-lg border"
                      style={{ background: z.color, borderColor: z.border }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Zone secici */}
          <div className="ml-8 flex flex-wrap gap-2 mb-6">
            {(Object.keys(TOKENS.zones) as ZoneKey[]).map((key) => {
              const z = TOKENS.zones[key];
              const ZIcon = z.icon;
              const isActive = activeZone === key;
              return (
                <button
                  key={key}
                  onClick={() => setActiveZone(key)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all border ${
                    isActive
                      ? "bg-white shadow-sm"
                      : "bg-transparent border-transparent hover:bg-white"
                  }`}
                  style={
                    isActive
                      ? { borderColor: z.color, color: z.color }
                      : { color: "#57534E" }
                  }
                >
                  <ZIcon className="w-3.5 h-3.5" style={{ color: isActive ? z.color : "#A8A29E" }} />
                  {z.label}
                  <span className="font-mono text-[10px] opacity-50">{z.pages}</span>
                </button>
              );
            })}
          </div>

          {/* Aktif zone — tokens + canli demo */}
          <div className="ml-8 grid lg:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ background: TOKENS.zones[activeZone].color }}
                />
                <span className="font-mono text-xs text-stone-500 uppercase tracking-widest">
                  zones.{activeZone}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-4">
                <ColorChip name={`${activeZone}.color`} value={TOKENS.zones[activeZone].color} />
                <ColorChip name={`${activeZone}.soft`} value={TOKENS.zones[activeZone].soft} />
                <ColorChip name={`${activeZone}.border`} value={TOKENS.zones[activeZone].border} />
                <ColorChip name={`${activeZone}.text`} value={TOKENS.zones[activeZone].text} />
              </div>
              <div className="bg-stone-100 border border-stone-200 rounded-xl p-4">
                <div className="text-[10px] font-mono uppercase tracking-widest text-stone-500 mb-2">
                  Kullanim yeri
                </div>
                <ul className="text-sm text-stone-700 space-y-1.5">
                  <li className="flex items-start gap-2">
                    <span className="text-stone-300 mt-1">•</span>
                    <span>Sayfa header&apos;indaki <span className="font-mono text-xs">SectionLabel</span></span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-stone-300 mt-1">•</span>
                    <span>Sidebar tezgah ikonu</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-stone-300 mt-1">•</span>
                    <span>Stat kartlarindaki ikon arka plani (<span className="font-mono text-xs">soft</span>)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-stone-300 mt-1">•</span>
                    <span>Aktif sayfa vurgusu (sidebar)</span>
                  </li>
                </ul>
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ background: TOKENS.zones[activeZone].color }}
                />
                <span className="font-mono text-xs text-stone-500 uppercase tracking-widest">
                  Canli sayfa gorunumu
                </span>
              </div>
              <DemoSnapshot zoneKey={activeZone} />
            </div>
          </div>
        </section>

        {/* SECTION 05 — SEMANTIC */}
        <section className="mb-16">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="font-mono text-xs text-stone-400">05</span>
            <h2 className="font-display italic text-2xl font-semibold">Semantic</h2>
          </div>
          <p className="text-sm text-stone-500 mb-6 ml-8">
            Success, warning, error, info — durum bildirimi. Tezgahtan bagimsiz.
          </p>

          <div className="grid md:grid-cols-2 gap-3">
            {Object.entries(TOKENS.semantic).map(([key, val]) => (
              <div key={key} className="bg-white border border-stone-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full" style={{ background: val.DEFAULT }} />
                  <span className="font-mono text-xs text-stone-500 uppercase tracking-widest">{key}</span>
                </div>
                <div className="grid grid-cols-4 gap-1.5 mb-3">
                  <ColorChip name="DEFAULT" value={val.DEFAULT} />
                  <ColorChip name="soft" value={val.soft} />
                  <ColorChip name="border" value={val.border} />
                  <ColorChip name="text" value={val.text} />
                </div>
                <div
                  className="px-3 py-2 rounded-lg text-xs font-medium border flex items-center gap-2"
                  style={{ background: val.soft, color: val.text, borderColor: val.border }}
                >
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: val.DEFAULT }} />
                  Bu bir {key} mesaji
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* SECTION 06 — ILKELER */}
        <section className="mb-16">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="font-mono text-xs text-stone-400">06</span>
            <h2 className="font-display italic text-2xl font-semibold">Ilkeler</h2>
          </div>

          <div className="ml-8 grid md:grid-cols-2 gap-3">
            {[
              { rule: "DO", title: "Tek zemin", body: "Tum uygulama stone-50 ustunde. Tezgahlar arasi geciste arka plan degismez." },
              { rule: "DO", title: "Renk = anlam", body: "Her zone rengi bir dile sahiptir. Slate=tarafsiz, Violet=yargi, Teal=harita, Stone=murekkep, Rose=kursu." },
              { rule: "DO", title: "Marka her yerde ayni", body: "Birincil buton her zaman indigo→violet gradient. Zone'a gore degismez." },
              { rule: "DO", title: "Amber'i koru", body: "Amber sadece danisman, Pro, hint icin. Sayfada en fazla iki yerde gorunmeli." },
              { rule: "DON'T", title: "Zone rengini gradient'e karistirma", body: "Birincil buton sabittir. Zone rengiyle ezilen butonlar yapma." },
              { rule: "DON'T", title: "Zemini boyama", body: "Tezgah icin arka plan rengi degistirmek flicker yaratir ve tutarsiz hisseder." },
            ].map((p) => (
              <div key={p.title} className="bg-white border border-stone-200 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold"
                    style={{
                      background: p.rule === "DO" ? "#D1FAE5" : "#FEE2E2",
                      color: p.rule === "DO" ? "#065F46" : "#991B1B",
                    }}
                  >
                    {p.rule}
                  </span>
                  <span className="font-display italic text-base font-semibold text-stone-900">{p.title}</span>
                </div>
                <p className="text-sm text-stone-600 leading-relaxed">{p.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* SECTION 07 — EXPORT */}
        <section className="mb-10">
          <div className="flex items-baseline gap-3 mb-1">
            <span className="font-mono text-xs text-stone-400">07</span>
            <h2 className="font-display italic text-2xl font-semibold">Export</h2>
          </div>
          <p className="text-sm text-stone-500 mb-6 ml-8">
            Token dosyasi
          </p>

          <div className="ml-8 bg-stone-900 rounded-xl overflow-hidden border border-stone-800">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-stone-800">
              <span className="font-mono text-xs text-stone-400">tokens.ts</span>
              <button
                onClick={() => {
                  const code = `// ${BRAND} Design Tokens — D2\nexport const tokens = ${JSON.stringify(TOKENS, null, 2).replace(/"([^"]+)":/g, "$1:")};`;
                  navigator.clipboard?.writeText(code);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium bg-stone-800 hover:bg-stone-700 text-stone-100 transition-colors"
              >
                <Copy className="w-3 h-3" />
                Kopyala
              </button>
            </div>
            <pre className="text-[11px] font-mono leading-relaxed overflow-x-auto p-4 text-stone-100">
{`export const tokens = {
  base: {
    bg: "${TOKENS.base.bg}",
    surface: "${TOKENS.base.surface}",
    border: "${TOKENS.base.border}",
    text: "${TOKENS.base.text}",
    textMuted: "${TOKENS.base.textMuted}",
  },
  brand: {
    gradient: "linear-gradient(135deg, ${TOKENS.brand.gradientFrom}, ${TOKENS.brand.gradientTo})",
    primary: "${TOKENS.brand.primary}",
  },
  accent: {  // KISITLI: danisman / Pro / hint
    DEFAULT: "${TOKENS.accent.DEFAULT}",
    soft: "${TOKENS.accent.soft}",
  },
  zones: {
    discovery: { color: "${TOKENS.zones.discovery.color}", soft: "${TOKENS.zones.discovery.soft}" },
    curation:  { color: "${TOKENS.zones.curation.color}",  soft: "${TOKENS.zones.curation.soft}"  },
    gapAtlas:  { color: "${TOKENS.zones.gapAtlas.color}",  soft: "${TOKENS.zones.gapAtlas.soft}"  },
    authoring: { color: "${TOKENS.zones.authoring.color}", soft: "${TOKENS.zones.authoring.soft}" },
    defense:   { color: "${TOKENS.zones.defense.color}",   soft: "${TOKENS.zones.defense.soft}"   },
  },
};`}
            </pre>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="border-t border-stone-200 pt-6 text-xs text-stone-400 flex items-center justify-between flex-wrap gap-2">
          <span className="font-mono">D2 · Color Tokens · Internal Reference</span>
          <span>{BRAND} Design System</span>
        </footer>
      </div>
    </div>
  );
}
