"use client";

import React, { useCallback, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, ChevronRight, Menu, Settings } from "lucide-react";

import { useNavigation } from "@/lib/navigation-context";
import {
  useChatboxContext,
  useChatboxOpen,
  useCloseChatbox,
  useOpenChatbox,
} from "@/stores/ui";

import { BRAND } from "@/lib/brand";
import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";

import { PenIcon } from "./icons/pen";

export function Topbar() {
  const { breadcrumb, setMobileOpen } = useNavigation();
  const open = useChatboxOpen();
  const context = useChatboxContext();
  const openChatbox = useOpenChatbox();
  const closeChatbox = useCloseChatbox();
  const pathname = usePathname();

  // Sayfa label'ı breadcrumb'tan türetilir (en sağdaki segment)
  const pageLabel = breadcrumb[breadcrumb.length - 1] ?? BRAND;

  // DANISMAN_CHAT_TOPBAR_KONTEKST_KORUMA_2026-08-19: rapor sayfası kendi
  // context'ini (kind:"advisor", reportId) mount'ta zaten senkron tutuyor
  // (bkz [jobId]/page.tsx). Bu buton eskiden AÇARKEN context'i koşulsuz
  // {kind:"page"} ile eziyordu — kullanıcı rapor sayfasındayken bu kalem
  // ikonuna tıklayınca Danışman'ın rapor bağlamını kaybediyordu (gerçek
  // hata, 2026-08-19). /review/[jobId] rotasındayken mevcut context
  // korunur (context'siz openChatbox → "re-open quirk"); diğer tüm
  // sayfalarda eski davranış (generic page context) aynen kalır.
  const isReportRoute = pathname?.startsWith("/review/") ?? false;

  const toggleChatbox = useCallback(() => {
    if (open) closeChatbox();
    else if (isReportRoute && context) openChatbox();
    else openChatbox({ kind: "page", pageId: pageLabel, label: pageLabel });
  }, [open, openChatbox, closeChatbox, pageLabel, isReportRoute, context]);

  // Cmd+J / Ctrl+J global shortcut — Cmd+K (P049) çakışmaz
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && (e.key === "j" || e.key === "J")) {
        e.preventDefault();
        toggleChatbox();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleChatbox]);

  return (
    <nav
      className="sticky top-0 z-40 border-b border-stone-200 bg-white/80 backdrop-blur-md"
      style={{ height: "60px" }}
    >
      <div className="flex h-full items-center justify-between px-4 md:px-6">
        <div className="flex items-center gap-3">
          {/* Mobile menu */}
          <button
            onClick={() => setMobileOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-stone-600 transition-colors hover:bg-stone-100 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Wordmark */}
          <div className="mr-4 flex items-center">
            <ArbitraWordmark size="md" />
          </div>

          {/* Breadcrumb */}
          <div className="hidden items-center gap-2 text-sm text-stone-500 md:flex">
            {breadcrumb.map((b, i) => (
              <React.Fragment key={i}>
                {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-stone-300" />}
                <span className={i === breadcrumb.length - 1 ? "font-medium text-stone-900" : ""}>
                  {b}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Danışman trigger — F4-S4 P078 (D16 Pen icon, Cmd+J) */}
          <button
            type="button"
            onClick={toggleChatbox}
            aria-label="Danışmana sor (Cmd+J)"
            data-state={open ? "open" : "closed"}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-stone-600 transition-colors hover:bg-stone-100 data-[state=open]:bg-stone-900 data-[state=open]:text-white"
          >
            <PenIcon className="h-4 w-4" />
          </button>

          <button className="relative flex h-9 w-9 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100">
            <Bell className="h-4 w-4" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-amber-500" />
          </button>
          <Link
            href="/settings"
            aria-label="Ayarlar"
            title="Ayarlar"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-900"
          >
            <Settings className="h-4 w-4" />
          </Link>
          <div
            className="font-display flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-sm font-semibold italic text-white"
            style={{ background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)" }}
          >
            R
          </div>
        </div>
      </div>
    </nav>
  );
}
