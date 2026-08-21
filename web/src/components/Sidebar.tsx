"use client";

import Link from "next/link";
import {
  Folder,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronsLeft,
  X,
  Check,
  Crown,
  Sparkles,
  Lock,
} from "lucide-react";
import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";
import { BRAND } from "@/lib/brand";
import { useNavigation } from "@/lib/navigation-context";
import {
  workbenches,
  toolItems,
  type WorkbenchPage,
} from "@/lib/nav-config";

type PageState = "completed" | "current" | "locked" | "pending";

function derivePageState(
  page: WorkbenchPage,
  pages: WorkbenchPage[],
  currentPageId: string | null,
): PageState {
  // F10-F1: demo path için "future page = pending" (locked değil) — kullanıcı
  // demo'da tezgah sayfaları arası serbest gezinebilsin. Lock policy
  // (paywall + tezgah önkoşulu) Phase 2/3'te tier-aware gerçek implementasyon
  // ile geri gelir. Bkz. docs/plans/F10_back_front_integration_demo_path.md §3
  const currentIdx = pages.findIndex((p) => p.id === currentPageId);
  const idx = pages.findIndex((p) => p.id === page.id);
  if (currentIdx === -1) return "pending";
  if (idx < currentIdx) return "completed";
  if (idx === currentIdx) return "current";
  return "pending";
}

function lockTooltipText(idx: number, pages: WorkbenchPage[]): string {
  const prev = idx > 0 ? pages[idx - 1] : undefined;
  if (!prev) return "Bu tezgahı önceki adımlardan sonra açabilirsin";
  return `Önce "${prev.label}" sayfasını tamamlamalısın`;
}

export function Sidebar() {
  const {
    collapsed,
    setCollapsed,
    mobileOpen,
    setMobileOpen,
    openWorkbench,
    setOpenWorkbench,
    activeProject,
    inProject,
    exitProject,
    currentPageId,
    navigateTo,
  } = useNavigation();

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          style={{ animation: "fadeIn 0.2s ease-out" }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`z-50 flex flex-shrink-0 flex-col border-r border-stone-200 bg-white transition-all duration-300
          ${collapsed ? "lg:w-16" : "lg:w-[280px]"}
          ${mobileOpen ? "fixed inset-y-0 left-0 w-[280px]" : "hidden lg:flex"}
        `}
        style={{
          height: mobileOpen ? "100vh" : "calc(100vh - 60px)",
          top: mobileOpen ? 0 : undefined,
        }}
      >
        {/* Mobile close */}
        {mobileOpen && (
          <button
            onClick={() => setMobileOpen(false)}
            className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg text-stone-500 hover:bg-stone-100 lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        {/* Arbitra wordmark — tıklanınca /landing */}
        <div className="border-b border-stone-100">
          {!collapsed ? (
            <Link
              href="/landing"
              className="flex items-center px-4 pb-2.5 pt-3 transition-colors hover:bg-stone-50"
              title="Pazarlama sayfasına dön"
            >
              <ArbitraWordmark size="md" />
            </Link>
          ) : (
            <Link
              href="/landing"
              className="flex items-center justify-center px-2 py-3 transition-colors hover:bg-stone-50"
              title="Pazarlama sayfasına dön"
              aria-label={BRAND}
            >
              {/* Daraltılmış sidebar — monogram: markanın aksanlı ilk harfi
                  (ArbitraWordmark ile aynı font-display dili). Gerçek glyph
                  Omer onayı bekliyor. */}
              <span
                aria-hidden="true"
                className="font-display text-[20px] font-medium tracking-[0.04em] text-ink"
                style={{ color: "var(--color-accent)" }}
              >
                {BRAND[0]}
              </span>
            </Link>
          )}
        </div>

        {/* Workspace switcher */}
        <div className="border-b border-stone-100 p-3">
          {!collapsed ? (
            <button className="group flex w-full items-center gap-2.5 rounded-xl p-2 transition-colors hover:bg-stone-50">
              <div
                className="font-display flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-sm font-semibold italic text-white"
                style={{ background: "var(--color-ink)" }}
              >
                R
              </div>
              <div className="min-w-0 flex-1 text-left">
                <div className="truncate text-sm font-semibold text-stone-900">Prof. Rencber</div>
                <div className="truncate text-xs text-stone-500">Ücretsiz plan</div>
              </div>
              <ChevronDown className="h-4 w-4 flex-shrink-0 text-stone-400" />
            </button>
          ) : (
            <div
              className="font-display mx-auto flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold italic text-white"
              style={{ background: "var(--color-ink)" }}
            >
              R
            </div>
          )}
        </div>

        {/* Project header (in-project mode) — V1-S14 P003: activeProject null
            ise (proje yok / yanlış URL) blok render edilmez. */}
        {inProject && activeProject && !collapsed && (
          <div className="px-3 pt-3">
            <button
              onClick={exitProject}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-medium text-stone-500 transition-all hover:bg-stone-50 hover:text-stone-700"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Tum projelere don
            </button>
            <div
              className="mt-2 rounded-xl p-3"
              style={{
                background: `${activeProject.color}10`,
                border: `1px solid ${activeProject.color}30`,
              }}
            >
              <div className="mb-1 flex items-center gap-2">
                <div
                  className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg"
                  style={{ background: `${activeProject.color}20`, color: activeProject.color }}
                >
                  <Folder className="h-3.5 w-3.5" />
                </div>
                <div className="font-display truncate text-sm font-semibold italic text-stone-900">
                  {activeProject.name}
                </div>
              </div>
              <div className="ml-9 text-[10px] text-stone-500">{activeProject.paperCount} makale</div>
            </div>
          </div>
        )}

        {inProject && activeProject && collapsed && (
          <div className="px-2 pt-3">
            <div
              className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg"
              style={{ background: `${activeProject.color}20`, color: activeProject.color }}
            >
              <Folder className="h-4 w-4" />
            </div>
          </div>
        )}

        {/* Main nav content */}
        <div className="flex-1 overflow-y-auto px-3 pb-3 pt-5">
          {/* WORKBENCHES + TOOLS — her zaman görünür, default kapalı */}
          {(
            <>
              {!collapsed && (
                <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-stone-400">
                  Tezgahlar
                </div>
              )}

              <div className="space-y-0.5">
                {workbenches.map((wb) => {
                  const WbIcon = wb.icon;
                  const isOpen = openWorkbench === wb.id;
                  const hasActivePage = wb.pages.some((p) => p.id === currentPageId);

                  return (
                    <div key={wb.id}>
                      <button
                        onClick={() => {
                          if (collapsed) return;
                          setOpenWorkbench(isOpen ? null : wb.id);
                        }}
                        title={collapsed ? wb.label : undefined}
                        className="relative flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-stone-700 transition-all hover:bg-stone-50"
                        style={
                          hasActivePage
                            ? { background: "var(--color-bg-soft, #f1f5f9)", color: "var(--color-ink)" }
                            : undefined
                        }
                      >
                        {hasActivePage && !collapsed && (
                          <span
                            aria-hidden="true"
                            className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r"
                            style={{ background: "var(--color-accent)" }}
                          />
                        )}
                        {!collapsed &&
                          (isOpen ? (
                            <ChevronDown className="h-3 w-3 flex-shrink-0 text-stone-400" />
                          ) : (
                            <ChevronRight className="h-3 w-3 flex-shrink-0 text-stone-400" />
                          ))}
                        <WbIcon className="h-4 w-4 flex-shrink-0" style={{ color: wb.color }} strokeWidth={2} />
                        {!collapsed && (
                          <>
                            <span className="flex-1 truncate text-sm font-semibold">{wb.label}</span>
                            <span className="font-mono text-[10px] text-stone-400">{wb.pages.length}</span>
                          </>
                        )}
                      </button>

                      {!collapsed && isOpen && (
                        <div
                          className="mb-1 ml-4 mt-0.5 space-y-0.5 pl-3"
                          style={{ borderLeft: `2px solid ${wb.color}30`, borderRadius: "0 0 0 4px" }}
                        >
                          {wb.pages.map((page, pageIdx) => {
                            const state = derivePageState(page, wb.pages, currentPageId);
                            const isCurrent = state === "current";
                            const isCompleted = state === "completed";
                            const isLocked = state === "locked";

                            return (
                              <button
                                key={page.id}
                                onClick={() => {
                                  if (!isLocked) navigateTo(page.id);
                                }}
                                disabled={isLocked}
                                title={
                                  isLocked
                                    ? lockTooltipText(pageIdx, wb.pages)
                                    : undefined
                                }
                                className={`group relative flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-all ${
                                  isLocked
                                    ? "cursor-not-allowed opacity-65"
                                    : "hover:bg-stone-50"
                                }`}
                                style={
                                  isCurrent
                                    ? {
                                        background: "rgba(79,70,229,0.07)",
                                        color: "var(--color-ink)",
                                        fontWeight: 500,
                                      }
                                    : isCompleted
                                      ? { color: "var(--color-ink-mute, #475569)" }
                                      : isLocked
                                        ? { color: "var(--color-ink-faint, #64748b)" }
                                        : { color: "var(--color-ink-mute, #475569)" }
                                }
                              >
                                <span
                                  aria-hidden="true"
                                  className="flex h-3.5 w-3.5 flex-shrink-0 items-center justify-center"
                                >
                                  {isCurrent ? (
                                    <span
                                      className="pm-pulse-dot block h-1.5 w-1.5 rounded-full"
                                      style={{ background: "var(--color-accent)" }}
                                    />
                                  ) : isCompleted ? (
                                    <Check
                                      className="h-3 w-3"
                                      strokeWidth={3}
                                      style={{ color: "var(--color-accent)" }}
                                    />
                                  ) : isLocked ? (
                                    <Lock className="h-3 w-3" strokeWidth={2} />
                                  ) : null}
                                </span>
                                <span className="flex-1 truncate">{page.label}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Separator */}
              <div className="mx-2 my-3 border-t border-stone-200" />

              {!collapsed && (
                <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-stone-400">
                  Araclar
                </div>
              )}

              <div className="space-y-0.5">
                {toolItems.map((item) => {
                  const ItemIcon = item.icon;
                  const isActive = currentPageId === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => navigateTo(item.id)}
                      title={collapsed ? item.label : undefined}
                      className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left text-stone-700 transition-all hover:bg-stone-50"
                      style={
                        isActive
                          ? {
                              background: "rgba(79,70,229,0.07)",
                              color: "var(--color-ink)",
                            }
                          : undefined
                      }
                    >
                      <ItemIcon
                        className="h-4 w-4 flex-shrink-0"
                        style={{
                          color: isActive
                            ? "var(--color-accent)"
                            : "#a8a29e",
                        }}
                        strokeWidth={2}
                      />
                      {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Pro tier card */}
        {!collapsed && (
          <div className="border-t border-stone-100 p-3">
            <div
              className="relative overflow-hidden rounded-xl p-3"
              style={{
                background: "var(--color-accent-pale)",
                border: "1px solid rgba(79,70,229,0.18)",
              }}
            >
              <div className="relative">
                <div className="mb-2 flex items-center gap-1.5">
                  <Crown
                    className="h-3 w-3"
                    strokeWidth={2.5}
                    style={{ color: "var(--color-accent)" }}
                  />
                  <span
                    className="text-xs font-semibold"
                    style={{ color: "#312E81" }}
                  >
                    Pro&#39;ya yukselt
                  </span>
                </div>
                <div className="mb-3 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-[11px] text-stone-700">
                    <Check
                      className="h-3 w-3 flex-shrink-0"
                      strokeWidth={3}
                      style={{ color: "var(--color-accent)" }}
                    />
                    <span>Sinirsiz proje</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-stone-700">
                    <Check
                      className="h-3 w-3 flex-shrink-0"
                      strokeWidth={3}
                      style={{ color: "var(--color-accent)" }}
                    />
                    <span>Juri + hakemlik</span>
                  </div>
                </div>
                <button
                  className="group/upgrade flex w-full items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold text-white transition-colors duration-150"
                  style={{ background: "var(--color-ink)" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "var(--color-accent)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "var(--color-ink)";
                  }}
                >
                  <Sparkles className="h-3 w-3" />
                  Yukselt
                </button>
              </div>
            </div>

            <div className="mt-2 px-1">
              <div className="mb-1 flex items-center justify-between text-[10px] text-stone-500">
                <span>Ucretsiz plan</span>
                <span className="font-mono">2/2 proje</span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-stone-100">
                <div
                  className="h-full rounded-full"
                  style={{ width: "100%", background: "var(--color-accent)" }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Collapse toggle */}
        <div className="hidden border-t border-stone-100 p-2 lg:block">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex w-full items-center justify-center rounded-lg p-2 text-stone-500 transition-colors hover:bg-stone-50"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          </button>
        </div>
      </aside>
    </>
  );
}
