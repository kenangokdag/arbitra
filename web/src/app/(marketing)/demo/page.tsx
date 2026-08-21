"use client";

import { useState } from "react";
import {
  Search, Plus, User, Settings, ChevronLeft, ChevronRight, ChevronDown,
  Sparkles, ArrowUp, BookOpen, FileText, Compass, Gavel, MessagesSquare,
  Check, X, Bookmark, ExternalLink, Copy, SortDesc,
  AlertCircle, ThumbsUp, ThumbsDown, Crown, Lock, Download, Eye,
  CircleCheck, GripVertical, BookMarked, ChevronsLeft, Bell, Map, PenTool, Shield,
  MessageSquare, Star, Home,
} from "lucide-react";
import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";

/* ============================================================
   COMMON COMPONENTS
   ============================================================ */

function SectionLabel({ children, icon: Icon }: { children: React.ReactNode; icon?: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
      {Icon ? <Icon className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />}
      {children}
    </div>
  );
}

function ProBadge({ size = "sm" }: { size?: "sm" | "md" }) {
  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold rounded-md text-white ${size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs"}`}
      style={{ background: "linear-gradient(135deg, #D97706 0%, #B45309 100%)" }}
    >
      <Crown className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} strokeWidth={2.5} />
      PRO
    </span>
  );
}

function GradientButton({ children, icon: Icon, size = "md", onClick, className = "" }: {
  children: React.ReactNode; icon?: React.ComponentType<{ className?: string }>; size?: "sm" | "md" | "lg"; onClick?: () => void; className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex items-center gap-2 font-medium rounded-xl text-white transition-all hover:scale-[1.02] active:scale-[0.98] ${
        size === "sm" ? "px-3.5 py-2 text-sm" : size === "lg" ? "px-6 py-3.5" : "px-4 py-2.5 text-sm"
      } ${className}`}
      style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)", boxShadow: "0 1px 2px rgba(79,70,229,0.2), 0 4px 12px -2px rgba(79,70,229,0.25)" }}
    >
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

function OutlineButton({ children, icon: Icon, onClick, className = "", size = "md" }: {
  children: React.ReactNode; icon?: React.ComponentType<{ className?: string }>; onClick?: () => void; className?: string; size?: "sm" | "md";
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 font-medium rounded-xl border border-stone-300 bg-white text-stone-800 hover:border-stone-400 hover:bg-stone-50 transition-all ${
        size === "sm" ? "px-3 py-2 text-sm" : "px-4 py-2.5 text-sm"
      } ${className}`}
    >
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

/* ============================================================
   ESTRA BARS — 4 boyut (E/M/C/T)
   ============================================================ */
type EstraScores = { e: number; m: number; c: number; t: number };

function EstraBars({ scores, size = "sm" }: { scores: EstraScores; size?: "sm" | "md" }) {
  const labels: Record<string, string> = { e: "E", m: "M", c: "C", t: "T" };
  return (
    <div className="flex items-end gap-0.5">
      {(Object.entries(scores) as [string, number][]).map(([key, val]) => (
        <div key={key} className="flex flex-col items-center gap-0.5" title={`${labels[key]}: ${val}`}>
          <div className={`${size === "sm" ? "w-1.5" : "w-2"} rounded-sm relative overflow-hidden`}
            style={{ height: size === "sm" ? 16 : 24, background: "rgba(79,70,229,0.15)" }}>
            <div className="absolute bottom-0 left-0 right-0 rounded-sm"
              style={{ height: `${val}%`, background: `linear-gradient(180deg, #7C3AED ${100 - val}%, #4F46E5 100%)` }} />
          </div>
          <span className="text-[9px] font-mono text-stone-400">{labels[key]}</span>
        </div>
      ))}
    </div>
  );
}

/* ============================================================
   DECISION BAND
   ============================================================ */
type DecisionBand = "canon" | "strong_evidence" | "frontier" | "risk";

const BAND_CONFIG: Record<DecisionBand, { label: string; bg: string; text: string; border: string }> = {
  canon: { label: "Kanonik kanıt", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  strong_evidence: { label: "Güçlü kanıt", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  frontier: { label: "Yenilik", bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  risk: { label: "Riskli", bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
};

/* ============================================================
   PAPER CARD
   ============================================================ */
type MockPaper = {
  id: string; title: string; authors: string; journal: string; year: number;
  citations: number; estra: EstraScores; decision_band: DecisionBand;
  method: string; quartile: string; openAccess: boolean; language: string;
  abstract: string;
};

function PaperCard({ paper, compact = false }: { paper: MockPaper; compact?: boolean }) {
  const band = BAND_CONFIG[paper.decision_band];
  return (
    <div className="group rounded-2xl border border-stone-200 bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-lg">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="font-display mb-1.5 cursor-pointer text-lg font-semibold italic leading-snug text-stone-900 transition-colors group-hover:text-indigo-700">
            {paper.title}
          </h3>
          <div className="text-sm text-stone-600">
            <span>{paper.authors}</span>
            <span className="mx-1.5 text-stone-400">·</span>
            <span className="italic">{paper.journal}</span>
            <span className="mx-1.5 text-stone-400">·</span>
            <span>{paper.year}</span>
            <span className="mx-1.5 text-stone-400">·</span>
            <span className="text-stone-500">{paper.citations} atıf</span>
          </div>
        </div>
        <div className="flex flex-shrink-0 items-center gap-3">
          <EstraBars scores={paper.estra} />
          <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${band.bg} ${band.text} ${band.border}`}>
            {band.label}
          </span>
        </div>
      </div>

      {!compact && paper.abstract && (
        <p className="mb-4 line-clamp-2 text-sm leading-relaxed text-stone-600">{paper.abstract}</p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          <span className="rounded-md border border-indigo-100 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">{paper.method}</span>
          <span className="rounded-md border border-stone-200 bg-stone-50 px-2 py-0.5 text-[11px] font-medium text-stone-600">{paper.quartile}</span>
          {paper.openAccess && (
            <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">Açık erişim</span>
          )}
          <span className="rounded-md border border-stone-200 bg-stone-50 px-2 py-0.5 text-[11px] font-medium text-stone-500">
            {paper.language === "en" ? "EN" : paper.language === "tr" ? "TR" : "ID"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-100" title="Özetle"><FileText className="h-3.5 w-3.5" /></button>
          <button className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-100" title="Sohbet"><Sparkles className="h-3.5 w-3.5" /></button>
          <button className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-100" title="Scholar"><ExternalLink className="h-3.5 w-3.5" /></button>
          <button className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-100" title="Atıf kopyala"><Copy className="h-3.5 w-3.5" /></button>
          <div className="mx-1 h-4 w-px bg-stone-200" />
          <button className="rounded-lg p-1.5 text-emerald-600 transition-colors hover:bg-emerald-50" title="Kabul et"><ThumbsUp className="h-3.5 w-3.5" /></button>
          <button className="rounded-lg p-1.5 text-stone-400 transition-colors hover:bg-stone-100" title="Reddet"><ThumbsDown className="h-3.5 w-3.5" /></button>
          <button className="rounded-lg p-1.5 text-amber-600 transition-colors hover:bg-amber-50" title="Listeme ekle"><Bookmark className="h-3.5 w-3.5" /></button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   MOCK DATA
   ============================================================ */
const MOCK_PAPERS: MockPaper[] = [
  {
    id: "W2024001", title: "Multi-Criteria Decision Making in Higher Education Accreditation: A Turkish Case Study",
    authors: "Yilmaz, A., Kara, B., ve 3 diger", journal: "Studies in Higher Education", year: 2024, citations: 47,
    estra: { e: 88, m: 92, c: 75, t: 81 }, decision_band: "canon", method: "Nicel", quartile: "Q1",
    openAccess: true, language: "en",
    abstract: "This study explores the application of multi-criteria decision making (MCDM) frameworks within the context of Turkish higher education accreditation processes, focusing on how institutional quality is measured and benchmarked.",
  },
  {
    id: "W2023042", title: "AHP-TOPSIS Hybrid Approach for University Quality Assessment",
    authors: "Demir, M., Sahin, K., ve 2 diger", journal: "European Journal of Education", year: 2023, citations: 124,
    estra: { e: 92, m: 88, c: 79, t: 85 }, decision_band: "strong_evidence", method: "Meta-analiz", quartile: "Q1",
    openAccess: false, language: "en",
    abstract: "We propose a hybrid AHP-TOPSIS approach to evaluate university quality across multiple dimensions, validated through case studies from 12 institutions across Europe and Turkiye.",
  },
  {
    id: "W2024089", title: "Stakeholder Perspectives on Accreditation Criteria",
    authors: "Aydin, F., Celik, R.", journal: "Quality in Higher Education", year: 2024, citations: 18,
    estra: { e: 65, m: 71, c: 68, t: 72 }, decision_band: "frontier", method: "Nitel", quartile: "Q2",
    openAccess: true, language: "en",
    abstract: "Through semi-structured interviews with 34 stakeholders, this paper examines diverging perspectives on what constitutes meaningful accreditation criteria.",
  },
  {
    id: "W2023117", title: "ENTROPY-VIKOR Method for Educational Quality Indicators",
    authors: "Ozturk, S., Polat, H., ve 4 diger", journal: "Computers & Education", year: 2023, citations: 89,
    estra: { e: 81, m: 85, c: 88, t: 79 }, decision_band: "strong_evidence", method: "Nicel", quartile: "Q1",
    openAccess: true, language: "en",
    abstract: "This paper introduces an ENTROPY-VIKOR hybrid method specifically calibrated for educational quality indicators in K-12 and higher education contexts.",
  },
];

/* ============================================================
   SIDEBAR
   ============================================================ */
type NavItem = { id: string; label: string; icon: React.ComponentType<{ className?: string; strokeWidth?: number }>; locked?: boolean; pro?: boolean };

function Sidebar({ collapsed, setCollapsed, currentPage, setCurrentPage }: {
  collapsed: boolean; setCollapsed: (v: boolean) => void; currentPage: string; setCurrentPage: (v: string) => void;
}) {
  const mainNav: NavItem[] = [
    { id: "dashboard", label: "Ana Sayfa", icon: Home },
    { id: "search", label: "Makale Ara", icon: Search },
    { id: "top5", label: "Bana Önerilenler", icon: Star },
  ];
  const tools: NavItem[] = [
    { id: "chat", label: "Sohbet", icon: MessageSquare },
    { id: "reading", label: "Okuma Listem", icon: BookMarked },
  ];
  const proTools: NavItem[] = [
    { id: "jury", label: "Jüri simülasyonu", icon: Gavel, pro: true },
    { id: "review", label: "Hakemlik simülasyonu", icon: MessagesSquare, pro: true },
  ];
  const locked: NavItem[] = [
    { id: "map", label: "Konu Haritası", icon: Map, locked: true },
    { id: "writer", label: "Yazım Asistanı", icon: PenTool, locked: true },
    { id: "defense", label: "Tez Savunma Provası", icon: Shield, locked: true },
  ];

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const active = currentPage === item.id;
    const isLocked = item.locked;
    const isPro = item.pro;

    return (
      <button
        key={item.id}
        onClick={() => !isLocked && setCurrentPage(item.id)}
        className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-lg transition-all group text-left ${
          active ? (isPro ? "bg-amber-50 text-amber-900 border border-amber-200" : "bg-indigo-50 text-indigo-900")
          : isLocked ? "text-stone-400 cursor-not-allowed" : "text-stone-700 hover:bg-stone-50"
        }`}
        disabled={isLocked}
      >
        <Icon className={`h-4 w-4 flex-shrink-0 ${
          active ? (isPro ? "text-amber-600" : "text-indigo-600")
          : isLocked ? "text-stone-300" : "text-stone-400"
        }`} strokeWidth={2} />
        {!collapsed && (
          <>
            <span className="flex-1 truncate text-sm font-medium">{item.label}</span>
            {isLocked && <Lock className="h-3 w-3 flex-shrink-0 text-stone-300" />}
            {isPro && <Crown className="h-2.5 w-2.5 flex-shrink-0 text-amber-500" strokeWidth={2.5} />}
          </>
        )}
      </button>
    );
  };

  return (
    <aside className={`flex flex-shrink-0 flex-col border-r border-stone-200 bg-white transition-all duration-300 ${collapsed ? "w-16" : "w-[260px]"}`}
      style={{ height: "calc(100vh - 60px)" }}>
      {/* User profile */}
      <div className="border-b border-stone-100 p-3">
        {!collapsed ? (
          <div className="flex items-center gap-2.5 rounded-xl p-2">
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg font-display text-sm font-semibold italic text-white"
              style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)" }}>R</div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold text-stone-900">Prof. Rencber</div>
              <div className="truncate text-xs text-stone-500">Ücretsiz plan</div>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg font-display text-sm font-semibold italic text-white"
            style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)" }}>R</div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 pt-3">
        {!collapsed && <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-stone-400">Keşfet</div>}
        <div className="space-y-0.5">{mainNav.map(renderItem)}</div>

        {!collapsed && <div className="mb-2 mt-5 px-2 text-[10px] font-semibold uppercase tracking-widest text-stone-400">Araçlar</div>}
        <div className="mt-1 space-y-0.5">{tools.map(renderItem)}</div>

        {!collapsed && (
          <div className="mb-2 mt-5 flex items-center gap-1.5 px-2">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-stone-400">Pro araçlar</span>
            <Crown className="h-2.5 w-2.5 text-amber-500" strokeWidth={2.5} />
          </div>
        )}
        <div className="mt-1 space-y-0.5" style={!collapsed ? {
          background: "linear-gradient(180deg, rgba(245,158,11,0.04) 0%, rgba(217,119,6,0.02) 100%)",
          borderLeft: "2px solid rgba(217,119,6,0.3)", borderRadius: "0 8px 8px 0", padding: "4px 0 4px 6px", marginLeft: "-8px",
        } : {}}>
          {proTools.map(renderItem)}
        </div>

        {!collapsed && <div className="mb-2 mt-5 px-2 text-[10px] font-semibold uppercase tracking-widest text-stone-400">Yakında</div>}
        <div className="mt-1 space-y-0.5">{locked.map(renderItem)}</div>

        {/* Bottom nav */}
        {!collapsed && <div className="mb-2 mt-6 px-2 text-[10px] font-semibold uppercase tracking-widest text-stone-400">Hesap</div>}
        <div className="mt-1 space-y-0.5">
          {[
            { id: "settings", label: "Ayarlar", icon: Settings },
            { id: "profile", label: "Profilim", icon: User },
          ].map(renderItem)}
        </div>
      </div>

      {/* Tier card */}
      {!collapsed && (
        <div className="border-t border-stone-100 p-3">
          <div className="relative overflow-hidden rounded-xl p-3" style={{ background: "linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%)" }}>
            <div className="absolute -right-4 -top-4 h-16 w-16 rounded-full opacity-30 blur-2xl"
              style={{ background: "linear-gradient(135deg, #4F46E5, #D97706)" }} />
            <div className="relative">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-stone-700">Ücretsiz plan</span>
                <span className="font-mono text-[10px] text-stone-500">10/10 arama</span>
              </div>
              <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-white">
                <div className="h-full rounded-full" style={{ width: "100%", background: "linear-gradient(90deg, #4F46E5, #7C3AED)" }} />
              </div>
              <button className="flex w-full items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold text-white transition-all hover:scale-[1.02]"
                style={{ background: "linear-gradient(135deg, #D97706 0%, #B45309 100%)" }}>
                <Crown className="h-3 w-3" strokeWidth={2.5} />
                Pro&apos;ya yükselt
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="border-t border-stone-100 p-2">
        <button onClick={() => setCollapsed(!collapsed)} className="flex w-full items-center justify-center rounded-lg p-2 text-stone-500 transition-colors hover:bg-stone-50">
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        </button>
      </div>
    </aside>
  );
}

/* ============================================================
   TOP NAV
   ============================================================ */
function TopNav({ breadcrumb }: { breadcrumb?: string[] }) {
  return (
    <nav className="sticky top-0 z-40 border-b border-stone-200 bg-white/80 backdrop-blur-md" style={{ height: 60 }}>
      <div className="flex h-full items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="mr-4 flex items-center gap-2">
            <ArbitraWordmark size="md" />
          </div>
          {breadcrumb && (
            <div className="hidden items-center gap-2 text-sm text-stone-500 md:flex">
              {breadcrumb.map((b, i) => (
                <span key={i} className="flex items-center gap-2">
                  {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-stone-300" />}
                  <span className={i === breadcrumb.length - 1 ? "font-medium text-stone-900" : ""}>{b}</span>
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="relative flex h-9 w-9 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100">
            <Bell className="h-4 w-4" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-amber-500" />
          </button>
          <button className="flex h-9 w-9 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100">
            <Settings className="h-4 w-4" />
          </button>
          <div className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg font-display text-sm font-semibold italic text-white"
            style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)" }}>R</div>
        </div>
      </div>
    </nav>
  );
}

/* ============================================================
   DASHBOARD
   ============================================================ */
function DashboardPage({ setCurrentPage }: { setCurrentPage: (p: string) => void }) {
  const stats = [
    { label: "Okuma listenizde", value: 12, icon: BookMarked, color: "#4F46E5" },
    { label: "Yeni öneri makalesi", value: 3, icon: Star, color: "#7C3AED" },
    { label: "Bekleyen özet", value: 5, icon: FileText, color: "#D97706" },
    { label: "Bu ay okunan", value: 28, icon: BookOpen, color: "#10B981" },
  ];

  const activities = [
    { time: "2 saat once", text: "MCDM aramasında 8 yeni makale bulundu", icon: Search },
    { time: "Bu sabah", text: "3 makale okuma listesine eklendi", icon: Bookmark },
    { time: "Dun", text: "AHP-TOPSIS makalesi özetlendi", icon: FileText },
    { time: "Dun", text: "Bana Önerilenler guncellendi — 3 yeni öneri", icon: Star },
    { time: "3 gun once", text: "Okuma hedefi tamamlandı: 15/15", icon: CircleCheck },
  ];

  return (
    <div className="mx-auto max-w-[1200px] p-8">
      <div className="mb-10" style={{ animation: "slideUp 0.6s ease-out" }}>
        <SectionLabel icon={Sparkles}>Hoş geldin</SectionLabel>
        <h1 className="font-display mb-2 mt-3 text-4xl font-semibold italic text-stone-900 md:text-5xl">
          İyi çalışmalar,{" "}
          <span style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Prof. Rencber
          </span>
        </h1>
        <p className="text-lg text-stone-600">Bugun 3 yeni öneri makaleniz ve 5 bekleyen ozetiniz var.</p>
      </div>

      {/* Stats */}
      <div className="mb-10 grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="rounded-2xl border border-stone-200 bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-indigo-200"
              style={{ animation: `slideUp 0.6s ease-out ${i * 60}ms both` }}>
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg" style={{ background: `${s.color}15`, color: s.color }}>
                <Icon className="h-4 w-4" />
              </div>
              <div className="font-display mb-0.5 text-3xl font-semibold italic text-stone-900">{s.value}</div>
              <div className="text-sm text-stone-500">{s.label}</div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent papers */}
        <div className="lg:col-span-2">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="font-display text-2xl font-semibold italic text-stone-900">Son bulunan makaleler</h2>
            <GradientButton icon={Search} size="sm" onClick={() => setCurrentPage("search")}>Yeni arama</GradientButton>
          </div>
          <div className="space-y-4">
            {MOCK_PAPERS.slice(0, 2).map((p, i) => (
              <div key={p.id} style={{ animation: `slideUp 0.6s ease-out ${i * 80 + 200}ms both` }}>
                <PaperCard paper={p} compact />
              </div>
            ))}
          </div>
        </div>

        {/* Activity */}
        <div>
          <h2 className="font-display mb-5 text-2xl font-semibold italic text-stone-900">Son aktiviteler</h2>
          <div className="rounded-2xl border border-stone-200 bg-white p-2">
            {activities.map((a, i) => {
              const Icon = a.icon;
              return (
                <div key={i} className="flex cursor-pointer items-start gap-3 rounded-xl p-3 transition-colors hover:bg-stone-50"
                  style={{ animation: `slideUp 0.6s ease-out ${i * 60 + 300}ms both` }}>
                  <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg"
                    style={{ background: "linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%)", color: "#4F46E5" }}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-snug text-stone-800">{a.text}</p>
                    <p className="mt-0.5 text-xs text-stone-500">{a.time}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   SEARCH (Adaptive Chat)
   ============================================================ */
function SearchPage() {
  const [messages, setMessages] = useState([
    { role: "user" as const, content: "Sağlık alanında çok kriterli karar verme yöntemleri" },
    { role: "assistant" as const, content: "Güzel bir konu. Daha doğru sonuçlar için birkaç soru sormak istiyorum.\n\nHangi tür karar verme problemine odaklanmak istiyorsunuz?",
      chips: ["Hastane yer seçimi", "Tedavi karşılaştırması", "Tıbbi cihaz değerlendirmesi", "Hepsi"] },
    { role: "user" as const, content: "Tedavi karşılaştırması" },
    { role: "assistant" as const, content: "Anladım. Şimdi yöntemsel yaklaşımı netleştirelim — hangisi araştırmanıza daha yakın?",
      chips: ["AHP odaklı", "TOPSIS / VIKOR", "Hibrit yaklaşımlar", "Hepsi"] },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 60px)" }}>
      <div className="flex flex-shrink-0 items-center justify-between border-b border-stone-200 bg-white px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: "#4F46E515", color: "#4F46E5" }}>
            <Compass className="h-4 w-4" />
          </div>
          <div>
            <div className="font-display text-base font-semibold italic text-stone-900">Adaptif arama</div>
            <div className="text-xs text-stone-500">Niyetinizi anlıyor, sonuçları daraltıyorum</div>
          </div>
        </div>
        <OutlineButton icon={Eye} size="sm" onClick={() => {}}>Sonuclari gor</OutlineButton>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-3xl space-y-6">
          <div className="mb-8 text-center">
            <SectionLabel icon={Compass}>Adaptif arama</SectionLabel>
            <h2 className="font-display mb-1 mt-3 text-2xl font-semibold italic text-stone-900">Niyetinizi anlamaya çalışıyorum</h2>
            <p className="text-sm text-stone-500">Her cevabınız aramayı daraltır ve sonuçları iyileştirir.</p>
          </div>

          {messages.map((msg, i) => (
            <div key={i} style={{ animation: `fadeInUp 0.4s ease-out ${i * 100}ms both` }}>
              {msg.role === "user" ? (
                <div className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl rounded-br-md px-5 py-3 text-[15px] leading-relaxed text-white"
                    style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)" }}>
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg"
                    style={{ background: "linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%)", color: "#4F46E5" }}>
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 max-w-[80%] flex-1">
                    <div className="whitespace-pre-line rounded-2xl rounded-tl-md border border-stone-200 bg-stone-50 px-5 py-3.5 text-[15px] leading-relaxed text-stone-800">
                      {msg.content}
                    </div>
                    {"chips" in msg && msg.chips && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {msg.chips.map((chip: string) => (
                          <button key={chip} className="rounded-full border border-stone-200 bg-white px-3.5 py-1.5 text-sm font-medium text-stone-700 transition-all hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700">
                            {chip}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {thinking && (
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg"
                style={{ background: "linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%)", color: "#4F46E5" }}>
                <Sparkles className="h-4 w-4 animate-pulse" />
              </div>
              <div className="flex items-center gap-1 rounded-2xl rounded-tl-md border border-stone-200 bg-stone-50 px-5 py-4">
                {[0, 1, 2].map((d) => (
                  <span key={d} className="h-1.5 w-1.5 rounded-full bg-indigo-500" style={{ animation: `pulse 1s ease-in-out ${d * 0.2}s infinite` }} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-shrink-0 border-t border-stone-200 bg-white p-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border border-stone-200 bg-stone-50 p-2 transition-all focus-within:border-indigo-300 focus-within:bg-white">
            <textarea value={input} onChange={(e) => setInput(e.target.value)}
              placeholder="Konuyu daraltın veya yeni bir soru sorun..."
              rows={1} className="flex-1 resize-none bg-transparent px-3 py-2 text-[15px] text-stone-800 placeholder-stone-400 focus:outline-none" />
            <button className="flex h-10 w-10 items-center justify-center rounded-xl text-white transition-all hover:scale-105 active:scale-95"
              style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)" }}
              onClick={() => { if (input.trim()) { setMessages([...messages, { role: "user", content: input }]); setInput(""); setThinking(true); setTimeout(() => setThinking(false), 1500); } }}>
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 text-center text-[11px] text-stone-400">Arbitra makaleni üç bağımsız hakemin önüne çıkarır</p>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   RESULTS
   ============================================================ */
function ResultsPage() {
  return (
    <div className="flex" style={{ height: "calc(100vh - 60px)" }}>
      <aside className="w-72 flex-shrink-0 overflow-y-auto border-r border-stone-200 bg-white">
        <div className="p-5">
          <div className="mb-5 flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold italic text-stone-900">Filtreler</h3>
          </div>
          {/* Yil */}
          <div className="mb-6">
            <div className="mb-3 flex items-center justify-between">
              <label className="text-sm font-semibold text-stone-700">Yıl aralığı</label>
              <span className="font-mono text-xs text-stone-500">2018–2025</span>
            </div>
            <div className="px-1">
              <div className="relative h-1.5 rounded-full bg-stone-100">
                <div className="absolute h-full rounded-full" style={{ left: "30%", right: "10%", background: "linear-gradient(90deg, #4F46E5, #7C3AED)" }} />
              </div>
            </div>
          </div>
          {/* Dil */}
          <div className="mb-6">
            <label className="mb-3 block text-sm font-semibold text-stone-700">Dil</label>
            <div className="space-y-2">
              {[{ label: "İngilizce", count: 156, checked: true }, { label: "Türkçe", count: 42, checked: true }, { label: "Endonezce", count: 8, checked: false }].map((m) => (
                <label key={m.label} className="flex cursor-pointer items-center gap-2.5">
                  <input type="checkbox" defaultChecked={m.checked} className="h-4 w-4 rounded accent-indigo-600" />
                  <span className="flex-1 text-sm text-stone-700">{m.label}</span>
                  <span className="font-mono text-xs text-stone-400">{m.count}</span>
                </label>
              ))}
            </div>
          </div>
          {/* Karar bandi */}
          <div className="mb-6">
            <label className="mb-3 block text-sm font-semibold text-stone-700">Kanıt kalitesi</label>
            <div className="space-y-2">
              {(["canon", "strong_evidence", "frontier", "risk"] as DecisionBand[]).map((band) => {
                const cfg = BAND_CONFIG[band];
                return (
                  <label key={band} className="flex cursor-pointer items-center gap-2.5">
                    <input type="checkbox" defaultChecked={band !== "risk"} className="h-4 w-4 rounded accent-indigo-600" />
                    <span className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${cfg.bg} ${cfg.text} ${cfg.border}`}>{cfg.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
          {/* Açık erişim */}
          <div className="mb-6">
            <label className="flex cursor-pointer items-center justify-between">
              <span className="text-sm font-semibold text-stone-700">Sadece açık erişim</span>
              <div className="relative h-5 w-9 rounded-full bg-stone-200"><div className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow" /></div>
            </label>
          </div>
        </div>
      </aside>

      <div className="flex-1 overflow-y-auto bg-stone-50">
        <div className="mx-auto max-w-4xl p-6">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <SectionLabel icon={CircleCheck}>23 sonuç bulundu</SectionLabel>
              <h1 className="font-display mt-2 text-3xl font-semibold italic text-stone-900">Sağlık + MCDM</h1>
            </div>
            <button className="flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 hover:bg-stone-50">
              <SortDesc className="h-3.5 w-3.5" /> Kanıt kalitesi <ChevronDown className="h-3 w-3" />
            </button>
          </div>
          <div className="space-y-4">
            {MOCK_PAPERS.map((p, i) => (
              <div key={p.id} style={{ animation: `slideUp 0.5s ease-out ${i * 80}ms both` }}><PaperCard paper={p} /></div>
            ))}
            <div className="flex justify-center pt-6"><OutlineButton icon={ChevronDown}>Daha fazla göster (19)</OutlineButton></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   PAPER DETAIL
   ============================================================ */
function PaperDetailPage() {
  const paper = MOCK_PAPERS[0]!;
  const band = BAND_CONFIG[paper.decision_band];

  return (
    <div className="overflow-y-auto" style={{ height: "calc(100vh - 60px)" }}>
      <div className="mx-auto max-w-6xl p-8">
        <div className="mb-6 flex items-center gap-2 text-sm text-stone-500">
          <ChevronLeft className="h-4 w-4" />
          <a className="cursor-pointer hover:text-indigo-600">Sonuçlara dön</a>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="rounded-md border border-indigo-100 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">{paper.method}</span>
              <span className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">Q1 dergi</span>
              <span className={`rounded-md border px-2.5 py-1 text-xs font-medium ${band.bg} ${band.text} ${band.border}`}>{band.label}</span>
              {paper.openAccess && <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">Açık erişim</span>}
            </div>
            <h1 className="font-display mb-5 text-3xl font-semibold italic leading-tight text-stone-900 md:text-4xl">{paper.title}</h1>
            <div className="mb-6 flex flex-wrap items-center gap-2 text-sm text-stone-600">
              <span className="font-medium">{paper.authors}</span><span className="text-stone-400">·</span>
              <span className="italic">{paper.journal}</span><span className="text-stone-400">·</span><span>{paper.year}</span>
            </div>

            <div className="mb-8 grid grid-cols-3 gap-3">
              <div className="rounded-xl border border-stone-200 bg-white p-4">
                <div className="mb-1 text-xs text-stone-500">Atıf</div>
                <div className="font-display text-2xl font-semibold italic text-stone-900">{paper.citations}</div>
              </div>
              <div className="rounded-xl border border-stone-200 bg-white p-4">
                <div className="mb-1 text-xs text-stone-500">DOI</div>
                <div className="truncate font-mono text-xs text-stone-700">10.1080/03075079...</div>
              </div>
              <div className="rounded-xl border border-stone-200 bg-white p-4">
                <div className="mb-1 text-xs text-stone-500">Yayin tarihi</div>
                <div className="text-sm font-medium text-stone-900">14 Mar 2024</div>
              </div>
            </div>

            <div className="mb-6 rounded-2xl border border-stone-200 bg-white p-7">
              <h2 className="font-display mb-4 text-xl font-semibold italic text-stone-900">Öz</h2>
              <p className="leading-relaxed text-stone-700">{paper.abstract}</p>
            </div>

            <div>
              <h2 className="font-display mb-4 text-xl font-semibold italic text-stone-900">Benzer makaleler</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {MOCK_PAPERS.slice(1, 3).map((p) => <PaperCard key={p.id} paper={p} compact />)}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* ESTRA */}
            <div className="rounded-2xl border border-stone-200 bg-white p-6">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-display text-lg font-semibold italic text-stone-900">ESTRA skoru</h3>
                <div className="font-display text-2xl font-semibold italic" style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>84</div>
              </div>
              <div className="space-y-3">
                {([
                  { label: "Kanıt gücü (E)", value: paper.estra.e },
                  { label: "Yöntem kalitesi (M)", value: paper.estra.m },
                  { label: "Atıf etkisi (C)", value: paper.estra.c },
                  { label: "Tema uyumu (T)", value: paper.estra.t },
                ] as const).map((d) => (
                  <div key={d.label}>
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-xs font-semibold text-stone-700">{d.label}</span>
                      <span className="font-mono text-xs text-stone-500">{d.value}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-stone-100">
                      <div className="h-full rounded-full" style={{ width: `${d.value}%`, background: "linear-gradient(90deg, #4F46E5, #7C3AED)" }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Faithfulness */}
            <div className="rounded-2xl border border-stone-200 bg-white p-6">
              <div className="mb-3 flex items-center gap-2">
                <h3 className="font-display text-lg font-semibold italic text-stone-900">Güven kartı</h3>
                <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">DOĞRULANDI</span>
              </div>
              <div className="space-y-2 text-sm">
                {[
                  { label: "JSON şema %100", ok: true },
                  { label: "LVR doğrulama >= 0.7", ok: true },
                  { label: "Çapraz validatör", ok: true },
                  { label: "MiniCheck NLI", ok: false, note: "Faz 3" },
                ].map((m) => (
                  <div key={m.label} className="flex items-center gap-2">
                    {m.ok ? <Check className="h-3.5 w-3.5 text-emerald-600" strokeWidth={3} /> : <X className="h-3.5 w-3.5 text-stone-400" strokeWidth={3} />}
                    <span className={m.ok ? "text-stone-700" : "text-stone-400"}>{m.label}</span>
                    {m.note && <span className="rounded bg-stone-100 px-1 text-[9px] text-stone-400">{m.note}</span>}
                  </div>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2 rounded-2xl border border-stone-200 bg-white p-4">
              <GradientButton icon={Sparkles} className="w-full justify-center">Sohbet başlat</GradientButton>
              <OutlineButton icon={FileText} className="w-full justify-center">Özetle</OutlineButton>
              <OutlineButton icon={ExternalLink} className="w-full justify-center">Google Scholar</OutlineButton>
              <OutlineButton icon={Copy} className="w-full justify-center">Atıf kopyala</OutlineButton>
              <OutlineButton icon={Bookmark} className="w-full justify-center">Listeme ekle</OutlineButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   READING LIST (Kanban)
   ============================================================ */
function ReadingListPage() {
  const columns = [
    { id: "todo", title: "Okunacak", color: "#94A3B8", bgColor: "bg-stone-50", papers: [MOCK_PAPERS[2]!, MOCK_PAPERS[3]!] },
    { id: "doing", title: "Okunuyor", color: "#D97706", bgColor: "bg-amber-50", papers: [MOCK_PAPERS[1]!] },
    { id: "done", title: "Okundu", color: "#10B981", bgColor: "bg-emerald-50", papers: [MOCK_PAPERS[0]!] },
  ];

  return (
    <div className="overflow-y-auto" style={{ height: "calc(100vh - 60px)" }}>
      <div className="mx-auto max-w-[1200px] p-8">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <SectionLabel icon={BookMarked}>Okuma listesi</SectionLabel>
            <h1 className="font-display mt-3 text-4xl font-semibold italic text-stone-900">Okuma yolculuğunuz</h1>
            <p className="mt-1 text-stone-600">Sürükleyip bırakarak makaleleri organize edin.</p>
          </div>
          <div className="flex items-center gap-2">
            <OutlineButton icon={Download} size="sm">RIS</OutlineButton>
            <OutlineButton icon={Download} size="sm">BibTeX</OutlineButton>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-4">
          <div className="grid gap-4 md:grid-cols-3 lg:col-span-3">
            {columns.map((col) => (
              <div key={col.id} className={`${col.bgColor} rounded-2xl border border-stone-200 p-3`}>
                <div className="mb-3 flex items-center justify-between px-2">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full" style={{ background: col.color }} />
                    <span className="font-display text-sm font-semibold italic text-stone-900">{col.title}</span>
                    <span className="rounded-md bg-white px-1.5 py-0.5 font-mono text-[10px] text-stone-500">{col.papers.length}</span>
                  </div>
                  <button className="rounded p-1 text-stone-400 hover:bg-white"><Plus className="h-3 w-3" /></button>
                </div>
                <div className="space-y-2">
                  {col.papers.map((p, i) => (
                    <div key={p.id} className="group cursor-grab rounded-xl border border-stone-200 bg-white p-3 transition-all hover:border-indigo-200 hover:shadow-md"
                      style={{ animation: `fadeInUp 0.4s ease-out ${i * 80}ms both` }}>
                      <div className="mb-2 flex items-start gap-2">
                        <GripVertical className="mt-0.5 h-3 w-3 flex-shrink-0 text-stone-300 opacity-0 transition-opacity group-hover:opacity-100" />
                        <h4 className="font-display flex-1 text-sm font-semibold italic leading-snug text-stone-900 line-clamp-3">{p.title}</h4>
                      </div>
                      <div className="mb-2 truncate text-xs text-stone-500">{p.authors}</div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-[10px] text-stone-400">{p.year}</span>
                          <span className="text-stone-300">·</span>
                          <span className="text-[10px] font-medium text-indigo-600">{p.method}</span>
                        </div>
                        <EstraBars scores={p.estra} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-stone-200 bg-white p-5">
              <h3 className="font-display mb-4 text-lg font-semibold italic text-stone-900">Bu hafta</h3>
              <div className="space-y-4">
                {[{ l: "Okunan", v: 12 }, { l: "Yer imi", v: 7 }, { l: "Reddedilen", v: 23 }].map((s) => (
                  <div key={s.l} className="flex items-center justify-between">
                    <span className="text-sm text-stone-600">{s.l}</span>
                    <span className="font-display text-2xl font-semibold italic text-stone-900">{s.v}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-white p-5">
              <h3 className="font-display mb-3 text-lg font-semibold italic text-stone-900">Hedef</h3>
              <div className="font-display text-3xl font-semibold italic text-stone-900">12<span className="text-xl text-stone-400">/15</span></div>
              <div className="mb-3 text-xs text-stone-500">Bu haftaki hedef</div>
              <div className="h-2 overflow-hidden rounded-full bg-stone-100">
                <div className="h-full rounded-full" style={{ width: "80%", background: "linear-gradient(90deg, #4F46E5, #7C3AED)" }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   JURY (Pro Preview)
   ============================================================ */
function JuryPage() {
  const reviewers = [
    { role: "Yöntem hakemi", tone: "Şüpheci", color: "#7C3AED", bg: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", score: 7.2,
      strengths: ["AHP-TOPSIS hibrit yaklasiminin ozgunlugu", "Örneklem büyüklüğü makul (n=247)", "İstatistiksel anlamlılık testleri uygulanmış"],
      weaknesses: ["Stratifikasyon dengesi tartışmalı", "Yanlılık kontrolü yetersiz", "Hassasiyet analizi eksik"] },
    { role: "Literatür hakemi", tone: "Kapsamlı", color: "#D97706", bg: "linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)", score: 8.4,
      strengths: ["Ulusal literatür güçlü kapsanmış", "Teorik çerçeve tutarlı", "Kavramsal harita net"],
      weaknesses: ["2023-2024 uluslararası çalışmalar eksik", "Karşıt görüşlere yer verilmemiş"] },
    { role: "Bulgu hakemi", tone: "Eleştirel", color: "#4F46E5", bg: "linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%)", score: 6.8,
      strengths: ["Bulgular istatistiksel olarak anlamlı", "Görselleştirme net", "Tablolar standart"],
      weaknesses: ["Nedensellik dili çok güçlü", "Sınırlılıklar bölümü yetersiz", "Pratik çıkarımlar zayıf"] },
  ];

  return (
    <div className="overflow-y-auto" style={{ height: "calc(100vh - 60px)" }}>
      <div className="mx-auto max-w-6xl p-8">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <SectionLabel icon={Gavel}>Jüri simülasyonu</SectionLabel>
            <h1 className="font-display mb-1 mt-3 text-4xl font-semibold italic text-stone-900">Üç hakem, üç bakış</h1>
            <p className="text-stone-600">Tezinizi savunmaya gitmeden önce sanal jüri ne diyor görün.</p>
          </div>
          <ProBadge size="md" />
        </div>

        <div className="grid gap-6 lg:grid-cols-4">
          <div className="space-y-6 lg:col-span-3">
            {reviewers.map((rev, i) => (
              <div key={rev.role} className="overflow-hidden rounded-2xl border border-stone-200 bg-white"
                style={{ animation: `slideUp 0.5s ease-out ${i * 100}ms both` }}>
                <div className="border-b border-stone-100 p-2" style={{ background: rev.bg }} />
                <div className="p-6">
                  <div className="mb-5 flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl" style={{ background: rev.bg }}>
                        <Gavel className="h-5 w-5" style={{ color: rev.color }} />
                      </div>
                      <div>
                        <div className="font-display text-xl font-semibold italic text-stone-900">{rev.role}</div>
                        <div className="text-sm italic" style={{ color: rev.color }}>{rev.tone} bakış</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="mb-0.5 text-xs text-stone-500">Puan</div>
                      <div className="font-display text-2xl font-semibold italic" style={{ color: rev.color }}>{rev.score}<span className="text-base text-stone-400">/10</span></div>
                    </div>
                  </div>
                  <div className="grid gap-5 md:grid-cols-2">
                    <div>
                      <div className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-widest text-emerald-700"><ThumbsUp className="h-3 w-3" />Güçlü yönler</div>
                      <ul className="space-y-2">{rev.strengths.map((s, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm leading-snug text-stone-700"><Check className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-600" strokeWidth={3} />{s}</li>
                      ))}</ul>
                    </div>
                    <div>
                      <div className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-widest text-amber-700"><AlertCircle className="h-3 w-3" />Zayıf yönler</div>
                      <ul className="space-y-2">{rev.weaknesses.map((w, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm leading-snug text-stone-700"><span className="mt-2 h-1 w-1 flex-shrink-0 rounded-full bg-amber-600" />{w}</li>
                      ))}</ul>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* DRS */}
          <div className="space-y-4">
            <div className="sticky top-6 rounded-2xl border border-stone-200 bg-white p-6">
              <div className="text-center">
                <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-stone-500">Defense Readiness Score</div>
                <div className="mb-5 text-xs text-stone-400">Savunma hazırlık puanı</div>
                <div className="relative mx-auto mb-4 h-40 w-40">
                  <svg className="-rotate-90 h-full w-full" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="44" stroke="#F5F5F4" strokeWidth="8" fill="none" />
                    <circle cx="50" cy="50" r="44" stroke="url(#drs-grad)" strokeWidth="8" fill="none"
                      strokeDasharray={`${74 * 2.76} 1000`} strokeLinecap="round" />
                    <defs><linearGradient id="drs-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#4F46E5" /><stop offset="100%" stopColor="#7C3AED" />
                    </linearGradient></defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <div className="font-display text-5xl font-semibold italic" style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>74</div>
                    <div className="mt-1 text-xs text-stone-500">/ 100</div>
                  </div>
                </div>
                <div className="mb-4 inline-block rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700">Ek revizyon önerilir</div>
              </div>
              <GradientButton icon={Download} className="mt-5 w-full justify-center">Raporu indir</GradientButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   MAIN APP
   ============================================================ */
export default function ArbitraDemo() {
  const [collapsed, setCollapsed] = useState(false);
  const [currentPage, setCurrentPage] = useState("dashboard");

  const breadcrumbs: Record<string, string[]> = {
    dashboard: ["Ana Sayfa"],
    search: ["Makale Ara"],
    results: ["Makale Ara", "Sonuclar"],
    detail: ["Makale Ara", "Sonuclar", "Makale"],
    top5: ["Bana Önerilenler"],
    chat: ["Sohbet"],
    reading: ["Okuma Listem"],
    jury: ["Pro", "Juri Simulasyonu"],
    review: ["Pro", "Hakemlik Simulasyonu"],
  };

  return (
    <div className="min-h-screen bg-stone-50">
      <style>{`
        .font-display { font-family: var(--font-lora), 'Lora', Georgia, serif; }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 0.3; transform: scale(1); } 50% { opacity: 1; transform: scale(1.4); } }
        .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .line-clamp-3 { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
      `}</style>

      <TopNav breadcrumb={breadcrumbs[currentPage]} />

      {/* Örnek veri uyarısı */}
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs font-medium text-amber-800">
        Bu sayfa tasarım önizlemesidir. Gösterilen makale verileri örnek veridir, gerçek veritabanından çekilmemiştir.
      </div>

      <div className="flex">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} currentPage={currentPage} setCurrentPage={setCurrentPage} />
        <main className="min-w-0 flex-1">
          {currentPage === "dashboard" && <DashboardPage setCurrentPage={setCurrentPage} />}
          {currentPage === "search" && <SearchPage />}
          {currentPage === "results" && <ResultsPage />}
          {currentPage === "detail" && <PaperDetailPage />}
          {currentPage === "reading" && <ReadingListPage />}
          {currentPage === "jury" && <JuryPage />}
          {currentPage === "top5" && <DashboardPage setCurrentPage={setCurrentPage} />}
          {currentPage === "chat" && <SearchPage />}
        </main>
      </div>
    </div>
  );
}
