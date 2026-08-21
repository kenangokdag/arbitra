"use client";

import {
  Sparkles,
  ArrowRight,
  Plus,
  Settings,
  Compass,
  Search,
  BookOpen,
  Map,
  PenTool,
  BarChart3,
  MessageSquare,
  ThumbsUp,
  CircleCheck,
  Globe,
  Lightbulb,
  Library,
  type LucideIcon,
} from "lucide-react";
import { BRAND } from "@/lib/brand";

// ============================================================
// Shared buttons
// ============================================================

function GradientButton({
  children,
  icon: Icon,
  size = "md",
  onClick,
}: {
  children: React.ReactNode;
  icon?: LucideIcon;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex items-center gap-2 rounded-xl font-medium text-white transition-all hover:scale-[1.02] active:scale-[0.98] ${
        size === "sm" ? "px-3.5 py-2 text-sm" : size === "lg" ? "px-6 py-3.5" : "px-4 py-2.5 text-sm"
      }`}
      style={{
        background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
        boxShadow: "0 1px 2px rgba(79, 70, 229, 0.2), 0 4px 12px -2px rgba(79, 70, 229, 0.25)",
      }}
    >
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

function OutlineButton({
  children,
  icon: Icon,
  onClick,
  size = "md",
}: {
  children: React.ReactNode;
  icon?: LucideIcon;
  onClick?: () => void;
  size?: "sm" | "md";
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 rounded-xl border border-stone-300 bg-white font-medium text-stone-800 transition-all hover:border-stone-400 hover:bg-stone-50 ${
        size === "sm" ? "px-3 py-2 text-sm" : "px-4 py-2.5 text-sm"
      }`}
    >
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

function SectionLabel({ children, icon: Icon }: { children: React.ReactNode; icon?: LucideIcon }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
      {Icon ? <Icon className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />}
      {children}
    </div>
  );
}

// ============================================================
// Data
// ============================================================

const STATS = [
  { label: "Yayin havuzu", Icon: Library, color: "#4F46E5", value: "100M+", sub: "senin icin indekslendi" },
  { label: "Kalite olcutu", Icon: BarChart3, color: "#7C3AED", value: "6", sub: "boyutta degerlendirme" },
  { label: "Yolculuk", Icon: Compass, color: "#4F46E5", value: "5", sub: "adimda birlikte" },
  { label: "Dil destegi", Icon: Globe, color: "#10B981", value: "12+", sub: "akademik dil" },
];

const JOURNEY = [
  { num: "01", title: "Aklindakini netlestir", desc: "Genis bir fikirle gel — sorularla beraber daraltiriz, yon sende kalir.", Icon: Compass },
  { num: "02", title: "Sana uygun makaleleri onerelim", desc: "100M+ yayini biz tarariz, en yakin olanlari sunariz. Begenmedigini elersin.", Icon: Search },
  { num: "03", title: "Hangisi daha guclu, beraber bakalim", desc: "Her makalenin gucunu 6 boyutta aclklariz — karari sen verirsin.", Icon: BookOpen },
  { num: "04", title: "Senin yerin literaturun neresinde?", desc: "Konunun haritada nereye dustugunu gosteririz, ozgun katki icin fikir veririz.", Icon: Map },
  { num: "05", title: "Yazima geldiginde de yanindayiz", desc: "Akademik dil onerileri, atif duzeni, juri provasi — yalniz birakmayiz.", Icon: PenTool },
];

const QUICK_START = [
  { id: "topic", title: "Bir cumleyle anlat", desc: "Aklindaki konuyu dogal dille soyle — gerisini birlikte yapariz", Icon: MessageSquare, color: "#4F46E5", primary: true },
  { id: "explore", title: "Once dolas, sonra basla", desc: "Hizli taramayla ne tur kaynaklar var bir bakmak istersen", Icon: Globe, color: "#4F46E5", primary: false },
  { id: "example", title: "Ornek projelere goz at", desc: "Baskalari nasil baslamis, hangi yolu izlemis — ilham al", Icon: Lightbulb, color: "#7C3AED", primary: false },
];

const PROMISES = ["Yorma yok", "Karar sende", "Aciklamalar seffaf", "Yorumlar danisman tonunda", "Yalniz birakmayiz"];

const EXAMPLES = ["Mesleki egitimde yapay zeka", "Erken cocuklukta dil gelisimi", "Yuksekogretimde kalite guvencesi"];

// ============================================================
// Main component
// ============================================================

export function JourneyProgressCard() {
  return (
    <div className="mx-auto max-w-[1400px] space-y-8 p-4 md:p-6">
      <style>{`
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* 1. Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <div
            className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl"
            style={{ background: "linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%)", color: "#4F46E5" }}
          >
            <Sparkles className="h-6 w-6" strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="mb-1.5 flex flex-wrap items-center gap-2">
              <SectionLabel icon={Sparkles}>Hos geldin</SectionLabel>
              <span className="rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-800">
                YENI PROJE
              </span>
            </div>
            <h1 className="font-display mb-1.5 text-3xl font-semibold italic leading-tight text-stone-900 md:text-4xl">
              Tek basina degilsin.
            </h1>
            <p className="max-w-2xl leading-relaxed text-stone-600">
              {BRAND}, akademik arastirmani kolaylastirmak icin yaninda. Sen aklindakini soyle,
              biz <span className="font-medium text-stone-800">100 milyondan fazla yayin</span> icinden senin icin en uygun olanlari oneririz.
              Karar her zaman sende.
            </p>
          </div>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <OutlineButton icon={Settings} size="sm">Sonra</OutlineButton>
          <GradientButton icon={Plus}>Konu yazmaya basla</GradientButton>
        </div>
      </div>

      {/* 2. Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {STATS.map((s) => (
          <div
            key={s.label}
            className="rounded-2xl border border-stone-200 bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-indigo-200"
          >
            <div className="mb-3 flex items-center justify-between">
              <div
                className="flex h-9 w-9 items-center justify-center rounded-lg"
                style={{ background: `${s.color}15`, color: s.color }}
              >
                <s.Icon className="h-4 w-4" />
              </div>
            </div>
            <div className="font-display text-3xl font-semibold italic leading-none text-stone-900">{s.value}</div>
            <div className="mt-2 text-sm text-stone-500">{s.label}</div>
            {s.sub && <div className="mt-0.5 text-xs text-stone-400">{s.sub}</div>}
          </div>
        ))}
      </div>

      {/* 3. Promise card */}
      <div className="relative overflow-hidden rounded-2xl border border-stone-200 bg-white p-7">
        <div
          className="absolute left-0 right-0 top-0 h-1"
          style={{ background: "linear-gradient(90deg, #4F46E5, #7C3AED)" }}
        />
        <div className="mb-4">
          <SectionLabel icon={Lightbulb}>Sen sec, biz onerelim</SectionLabel>
        </div>
        <p className="font-display mb-5 text-lg italic leading-relaxed text-stone-800 md:text-xl">
          &ldquo;Anahtar kelime aramaya, filtrelerle bogusma gerek yok. Sen aklindakini soyle,
          biz sana en uygun olanlari onerelim. Begenmedigini elersin, begendigini birlikte derinlestiririz.&rdquo;
        </p>
        <div className="flex flex-wrap gap-2 border-t border-stone-100 pt-4">
          <span className="mr-2 flex items-center text-xs font-semibold uppercase tracking-widest text-stone-500">
            Bizim sozumuz:
          </span>
          {PROMISES.map((chip) => (
            <span
              key={chip}
              className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700"
            >
              <CircleCheck className="h-3 w-3" strokeWidth={2.5} />
              {chip}
            </span>
          ))}
        </div>
      </div>

      {/* 4. Journey + Tip */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left — journey steps */}
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-2xl font-semibold italic text-stone-900">Yolculugun nasil ilerleyecek</h2>
            <span className="font-mono text-xs text-stone-500">5 adim</span>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-2">
            {JOURNEY.map((step, i) => (
              <div key={step.num} className="relative flex cursor-pointer items-start gap-3 rounded-xl p-4 transition-colors hover:bg-stone-50">
                {i < JOURNEY.length - 1 && (
                  <div className="absolute bottom-0 left-7 top-14 w-px bg-stone-100" />
                )}
                <div
                  className="relative z-10 mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
                  style={{ background: "linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%)", color: "#4F46E5" }}
                >
                  <step.Icon className="h-4 w-4" strokeWidth={2} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="font-mono text-[10px] font-semibold text-stone-400">{step.num}</span>
                    <h3 className="font-display text-base font-semibold italic leading-tight text-stone-900">{step.title}</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-stone-600">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right — tip card */}
        <div>
          <div className="mb-4">
            <h2 className="font-display text-2xl font-semibold italic text-stone-900">Nasil baslasam?</h2>
          </div>

          <div
            className="relative overflow-hidden rounded-2xl border p-6"
            style={{ background: "var(--color-accent-pale)", borderColor: "rgba(79,70,229,0.18)" }}
          >
            <div
              className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl"
              style={{ background: "var(--color-accent)" }}
            >
              <MessageSquare className="h-5 w-5 text-white" strokeWidth={2} />
            </div>
            <h3 className="font-display mb-2 text-xl font-semibold italic leading-tight text-stone-900">Bir cumleyle yeter</h3>
            <p className="mb-5 text-sm leading-relaxed text-stone-700">
              &ldquo;Turkiye&apos;de online egitimin etkilisi&rdquo; gibi.
              Anahtar kelime bulmaya calisma — gundelik dilini kullan.
            </p>
            <div className="space-y-2 border-t pt-4" style={{ borderColor: "rgba(79,70,229,0.18)" }}>
              <div
                className="mb-2 text-[10px] font-semibold uppercase tracking-widest"
                style={{ color: "#312E81" }}
              >
                Ya da soyle dene
              </div>
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  className="group flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs text-stone-700 transition-all hover:bg-white/70"
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = "var(--color-accent)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = "";
                  }}
                >
                  <span className="font-display italic">&ldquo;{example}&rdquo;</span>
                  <ArrowRight
                    className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100"
                    style={{ color: "var(--color-accent)" }}
                  />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 5. Quick start */}
      <div>
        <h2 className="font-display mb-4 text-2xl font-semibold italic text-stone-900">Nereden baslamak istersin?</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {QUICK_START.map((q) => (
            <button
              key={q.id}
              className="group relative overflow-hidden rounded-2xl border border-stone-200 bg-white p-6 text-left transition-all hover:-translate-y-1 hover:border-indigo-200 hover:shadow-lg"
            >
              <div
                className="absolute left-0 right-0 top-0 h-0.5 transition-all duration-300 group-hover:h-1"
                style={{
                  background: q.primary
                    ? "linear-gradient(90deg, #4F46E5, #7C3AED)"
                    : `linear-gradient(90deg, ${q.color}, ${q.color}aa)`,
                }}
              />
              <div className="mb-4 flex items-start justify-between">
                <div
                  className="flex h-12 w-12 items-center justify-center rounded-xl transition-transform group-hover:rotate-3 group-hover:scale-110"
                  style={{ background: `${q.color}15`, color: q.color }}
                >
                  <q.Icon className="h-5 w-5" strokeWidth={2} />
                </div>
                {q.primary && (
                  <span className="rounded-md border border-indigo-100 bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
                    ONERILEN
                  </span>
                )}
              </div>
              <h3 className="font-display mb-1.5 text-xl font-semibold italic leading-tight text-stone-900 transition-colors group-hover:text-indigo-700">
                {q.title}
              </h3>
              <p className="mb-3 text-sm leading-relaxed text-stone-600">{q.desc}</p>
              <div className="flex items-center gap-1 text-xs font-medium text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100">
                Ac
                <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Footer note */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-200 bg-white p-5">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl"
            style={{ background: "#F0FDFA", color: "#0E4F4A" }}
          >
            <ThumbsUp className="h-5 w-5" />
          </div>
          <div>
            <div className="font-display font-semibold italic text-stone-900">Tam fikrin oturmadiysa da olur</div>
            <div className="mt-0.5 text-xs text-stone-500">Sorularla birlikte sekillendiririz — utanilacak bir sey yok.</div>
          </div>
        </div>
        <GradientButton icon={ArrowRight}>Hadi baslayalim</GradientButton>
      </div>
    </div>
  );
}
