"use client";

import {
  BookOpen,
  Check,
  ChevronRight,
  Compass,
  FileText,
  Layers,
  Map,
  PenTool,
  ScrollText,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  X,
  type LucideIcon,
} from "lucide-react";

import { BRAND } from "@/lib/brand";

type Step = {
  num: number;
  name: string;
  feature: string;
  tag: string;
  covered: boolean;
  Icon: LucideIcon;
};

const STEPS: Step[] = [
  {
    num: 1,
    name: "Arastirma sorusu",
    feature: "Konu onerisi + kilitleme",
    tag: "1.1–1.2",
    covered: true,
    Icon: Target,
  },
  {
    num: 2,
    name: "Literatur arama",
    feature: "Onerilen + Hizli Tarama",
    tag: "2.1 + Hizli Tarama",
    covered: true,
    Icon: Search,
  },
  {
    num: 3,
    name: "Makale eleme",
    feature: "ESTRA 6-boyut skorlama",
    tag: "ESTRA",
    covered: true,
    Icon: Layers,
  },
  {
    num: 4,
    name: "Veri cikarma",
    feature: "Yapisal ozet + sentez",
    tag: "2.4–2.5",
    covered: true,
    Icon: FileText,
  },
  {
    num: 5,
    name: "Trend analizi",
    feature: "Bibliyometri + Bosluk + CD5",
    tag: "1.3 + 3.1 + 3.3",
    covered: true,
    Icon: TrendingUp,
  },
  {
    num: 6,
    name: "Yazim iyilestirme",
    feature: "Dil onerisi",
    tag: "4.3",
    covered: true,
    Icon: PenTool,
  },
  {
    num: 7,
    name: "Referans yonetimi",
    feature: "APA / MLA / BibTeX",
    tag: "4.4",
    covered: true,
    Icon: BookOpen,
  },
  {
    num: 8,
    name: "Intihal kontrolu",
    feature: "Dis arac kullan",
    tag: "Turnitin / iThenticate",
    covered: false,
    Icon: X,
  },
];

type UniqueFeature = {
  name: string;
  Icon: LucideIcon;
};

const UNIQUE_FEATURES: UniqueFeature[] = [
  { name: "Konu Kilitleme", Icon: Compass },
  { name: "504K Bosluk Haritasi", Icon: Map },
  { name: "Danisman", Icon: ScrollText },
  { name: "Simulasyon Odasi", Icon: Sparkles },
  { name: "ESTRA 6-Boyut", Icon: Layers },
  { name: "31.85M Ghost Kaynak", Icon: Search },
];

const COVERED = STEPS.filter((s) => s.covered).length;

function CheckCircle({ delay }: { delay: number }) {
  return (
    <span
      className="flex h-[18px] w-[18px] items-center justify-center rounded-full text-white"
      style={{
        background: "var(--color-accent)",
        animation: `pmCheckIn 400ms cubic-bezier(.2,.8,.3,1.2) ${delay}ms both`,
      }}
    >
      <Check className="h-2.5 w-2.5" strokeWidth={3} />
    </span>
  );
}

function CrossCircle() {
  return (
    <span
      className="flex h-[18px] w-[18px] items-center justify-center rounded-full"
      style={{
        background: "var(--color-rule-soft)",
        color: "var(--color-ink-faint)",
      }}
    >
      <X className="h-2.5 w-2.5" strokeWidth={2.5} />
    </span>
  );
}

function StepCell({ step, idx }: { step: Step; idx: number }) {
  const cellBg = step.covered ? "var(--color-bg-card)" : "var(--color-bg)";
  const tagBg = step.covered
    ? "var(--color-accent-pale)"
    : "var(--color-bg-soft)";
  const tagColor = step.covered
    ? "var(--color-accent)"
    : "var(--color-ink-faint)";
  const tagBorder = step.covered
    ? "rgba(180,83,9,0.15)"
    : "var(--color-rule)";
  return (
    <div
      className="relative px-[18px] py-4 transition-colors duration-150"
      style={{ background: cellBg }}
    >
      <div className="mb-2 flex items-start justify-between">
        <span
          className="font-mono text-[10px] font-medium tracking-wider"
          style={{ color: "var(--color-ink-faint)" }}
        >
          {String(step.num).padStart(2, "0")}
        </span>
        {step.covered ? <CheckCircle delay={idx * 100} /> : <CrossCircle />}
      </div>
      <div
        className="mb-1 text-[13px] font-semibold leading-tight"
        style={{
          color: step.covered ? "var(--color-ink)" : "var(--color-ink-mute)",
        }}
      >
        {step.name}
      </div>
      <div
        className="text-[11px] leading-snug"
        style={{ color: "var(--color-ink-faint)" }}
      >
        {step.feature}
        <span
          className="ml-1 inline-block rounded-full px-[7px] py-[2px] font-mono text-[10px] font-medium"
          style={{
            background: tagBg,
            color: tagColor,
            border: `1px solid ${tagBorder}`,
          }}
        >
          {step.tag}
        </span>
      </div>
    </div>
  );
}

function UniqueItem({ feature }: { feature: UniqueFeature }) {
  const Icon = feature.Icon;
  return (
    <div
      className="flex cursor-default flex-col items-center gap-1.5 rounded-[10px] bg-white p-3 text-center transition-colors duration-150"
      style={{ border: "1px solid var(--color-rule-soft)" }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(180,83,9,0.25)";
        e.currentTarget.style.background =
          "color-mix(in oklab, var(--color-accent-pale) 50%, white)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--color-rule-soft)";
        e.currentTarget.style.background = "white";
      }}
    >
      <div
        className="flex h-8 w-8 items-center justify-center rounded-lg"
        style={{
          background: "var(--color-accent-pale)",
          color: "var(--color-accent)",
        }}
      >
        <Icon className="h-4 w-4" strokeWidth={2} />
      </div>
      <span
        className="text-[11px] font-medium leading-tight"
        style={{ color: "var(--color-ink-soft)" }}
      >
        {feature.name}
      </span>
    </div>
  );
}

function WidgetVariant() {
  return (
    <div
      className="overflow-hidden rounded-[14px] bg-white"
      style={{
        border: "1px solid var(--color-rule-soft)",
        boxShadow:
          "0 1px 2px rgba(15,23,42,0.04), 0 4px 16px rgba(15,23,42,0.04)",
      }}
    >
      <style>{`
        @keyframes pmCheckIn {
          from { opacity: 0; transform: scale(0); }
          to   { opacity: 1; transform: scale(1); }
        }
      `}</style>

      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-[14px] pt-[18px]"
        style={{ borderBottom: "1px solid var(--color-rule-soft)" }}
      >
        <div>
          <h3
            className="font-display text-[16px] font-semibold leading-tight"
            style={{ color: "var(--color-ink)", letterSpacing: "-0.01em" }}
          >
            Literatur taramani tek catida yap
          </h3>
          <div
            className="mt-0.5 text-[12px]"
            style={{ color: "var(--color-ink-faint)" }}
          >
            8 adimin 7&#39;si {BRAND}&#39;da — dagintik arac kullanmana
            gerek yok
          </div>
        </div>
        <span
          className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-mono text-[11px] font-semibold"
          style={{
            background: "var(--color-accent-pale)",
            color: "var(--color-accent)",
            border: "1px solid rgba(180,83,9,0.2)",
          }}
        >
          {COVERED}/{STEPS.length}
          <Check className="-mt-px h-3 w-3" strokeWidth={3} />
        </span>
      </div>

      {/* 4×2 unified grid with shared 1px borders */}
      <div
        className="grid grid-cols-2 md:grid-cols-4"
        style={{
          gap: "1px",
          background: "var(--color-rule-soft)",
          borderBottom: "1px solid var(--color-rule-soft)",
        }}
      >
        {STEPS.map((step, idx) => (
          <StepCell key={step.num} step={step} idx={idx} />
        ))}
      </div>

      {/* Unique features */}
      <div
        className="px-6 py-[18px] pt-4"
        style={{ background: "var(--color-bg)" }}
      >
        <div
          className="mb-3 flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: "var(--color-ink-faint)" }}
        >
          +
          <span
            className="font-display text-[11.5px] font-medium normal-case italic"
            style={{
              color: "var(--color-accent)",
              letterSpacing: 0,
            }}
          >
            Sadece {BRAND}&#39;da
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {UNIQUE_FEATURES.map((f) => (
            <UniqueItem key={f.name} feature={f} />
          ))}
        </div>
      </div>
    </div>
  );
}

function OnboardingVariant({ userName }: { userName?: string }) {
  return (
    <div
      className="overflow-hidden rounded-2xl bg-white"
      style={{
        border: "1px solid var(--color-rule-soft)",
        boxShadow:
          "0 1px 2px rgba(15,23,42,0.04), 0 8px 32px rgba(15,23,42,0.06)",
      }}
    >
      <style>{`
        @keyframes pmCheckIn {
          from { opacity: 0; transform: scale(0); }
          to   { opacity: 1; transform: scale(1); }
        }
      `}</style>

      {/* Dark header w/ amber radial */}
      <div
        className="relative overflow-hidden px-8 pb-5 pt-7"
        style={{
          background: "var(--color-ink)",
          borderBottom: "1px solid var(--color-rule-soft)",
        }}
      >
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 80% 50%, rgba(232,161,87,0.15), transparent 60%)",
          }}
        />
        <div className="relative">
          <div
            className="mb-2.5 font-mono text-[10.5px] font-medium uppercase tracking-widest"
            style={{ color: "rgba(248,250,252,0.5)" }}
          >
            {BRAND} nedir?
          </div>
          <h2
            className="font-display text-[26px] font-semibold leading-[1.15]"
            style={{
              color: "#f8fafc",
              letterSpacing: "-0.015em",
            }}
          >
            Hos geldin,{" "}
            <em
              className="font-display"
              style={{ color: "#E8A157", fontStyle: "italic" }}
            >
              {userName ?? "Prof. Rencber."}
            </em>
          </h2>
          <p
            className="mt-2 max-w-[52ch] text-sm leading-[1.55]"
            style={{ color: "rgba(248,250,252,0.65)" }}
          >
            Literatur taramanin 8 adimindan 7&#39;sini burada yapacaksin.
            Dagintik araclara, farkli tablolara, kaybolan referanslara son.
          </p>

          <div className="relative mt-5">
            <div
              className="h-[3px] overflow-hidden rounded-[10px]"
              style={{ background: "rgba(248,250,252,0.12)" }}
            >
              <div
                className="h-full rounded-[10px] transition-[width] duration-1000 ease-out"
                style={{ width: "14%", background: "#E8A157" }}
              />
            </div>
            <div
              className="mt-1.5 flex justify-between font-mono text-[10px]"
              style={{ color: "rgba(248,250,252,0.4)" }}
            >
              <span>Baslangic</span>
              <span>Mezuniyet 🎓</span>
            </div>
          </div>
        </div>
      </div>

      {/* Step list */}
      <div className="flex flex-col gap-1 px-7 py-5">
        {STEPS.map((step) => {
          const Icon = step.covered ? Check : X;
          return (
            <div
              key={step.num}
              className="grid items-center gap-3 rounded-lg px-3 py-2.5 transition-colors duration-150 hover:bg-stone-50"
              style={{ gridTemplateColumns: "28px 1fr auto" }}
            >
              <div
                className="flex h-7 w-7 items-center justify-center rounded-lg"
                style={{
                  background: step.covered
                    ? "var(--color-accent)"
                    : "var(--color-bg-soft)",
                  color: step.covered ? "white" : "var(--color-ink-faint)",
                }}
              >
                <Icon className="h-3.5 w-3.5" strokeWidth={2.5} />
              </div>
              <div>
                <div
                  className="text-[13.5px] font-medium leading-tight"
                  style={{
                    color: step.covered
                      ? "var(--color-ink)"
                      : "var(--color-ink-mute)",
                  }}
                >
                  {step.name}
                </div>
                <div
                  className="mt-0.5 text-[11px]"
                  style={{ color: "var(--color-ink-faint)" }}
                >
                  {step.feature} · {step.tag}
                </div>
              </div>
              <span
                className="rounded-full px-2 py-[3px] font-mono text-[10.5px] font-medium"
                style={
                  step.covered
                    ? {
                        background: "var(--color-accent-pale)",
                        color: "var(--color-accent)",
                        border: "1px solid rgba(180,83,9,0.18)",
                      }
                    : {
                        background: "var(--color-bg-soft)",
                        color: "var(--color-ink-faint)",
                        border: "1px solid var(--color-rule-soft)",
                      }
                }
              >
                {step.covered ? `${BRAND} ✓` : "Dis arac"}
              </span>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div
        className="flex items-center gap-2.5 px-7 pb-5 pt-4"
        style={{ borderTop: "1px solid var(--color-rule-soft)" }}
      >
        <button
          type="button"
          className="font-display inline-flex h-10 items-center gap-[7px] rounded-lg px-5 text-sm font-semibold italic transition-colors"
          style={{
            background: "#E8A157",
            border: "1px solid #E8A157",
            color: "var(--color-ink)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "#D4923E";
            e.currentTarget.style.borderColor = "#D4923E";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "#E8A157";
            e.currentTarget.style.borderColor = "#E8A157";
          }}
        >
          Ilk projeyi olustur
          <ChevronRight className="h-3.5 w-3.5" strokeWidth={2.5} />
        </button>
        <button
          type="button"
          className="inline-flex h-10 items-center rounded-lg px-4 text-sm transition-colors"
          style={{
            background: "transparent",
            border: "1px solid var(--color-rule)",
            color: "var(--color-ink-mute)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--color-ink-soft)";
            e.currentTarget.style.color = "var(--color-ink)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--color-rule)";
            e.currentTarget.style.color = "var(--color-ink-mute)";
          }}
        >
          Nasil calisir?
        </button>
        <span
          className="font-display ml-auto text-[11.5px] italic"
          style={{ color: "var(--color-ink-faint)" }}
        >
          Kredi karti gerektirmez
        </span>
      </div>
    </div>
  );
}

export function JourneyProgress({
  variant = "widget",
  userName,
}: {
  variant?: "widget" | "onboarding";
  userName?: string;
}) {
  return variant === "onboarding" ? (
    <OnboardingVariant userName={userName} />
  ) : (
    <WidgetVariant />
  );
}
