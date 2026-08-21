// F14 Hakemlik — admin kabuk. Sidebar desenini sadeleştirir (admin nav).
// Sol panel: İşler · İstatistik. Sade, fonksiyonel, üst-seviye.

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, ListChecks, Palette, type LucideIcon } from "lucide-react";

import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";

type AdminNavItem = { href: string; label: string; icon: LucideIcon };

const ADMIN_NAV: AdminNavItem[] = [
  { href: "/admin", label: "İstatistik", icon: BarChart3 },
  { href: "/admin/jobs", label: "İşler", icon: ListChecks },
  { href: "/admin/theme", label: "Tema", icon: Palette },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-bg">
      <div className="flex">
        {/* Sol panel */}
        <aside className="flex w-[240px] flex-shrink-0 flex-col border-r border-rule bg-bg-soft">
          <div className="border-b border-rule px-4 py-4">
            <Link
              href="/admin"
              className="flex items-baseline gap-2 no-underline"
            >
              <ArbitraWordmark size="md" />
              <span className="font-mono-pmid text-[11px] uppercase tracking-[0.1em] text-ink-faint">
                Yönetim
              </span>
            </Link>
          </div>

          <nav className="flex flex-col gap-0.5 p-3">
            {ADMIN_NAV.map((item) => {
              const Icon = item.icon;
              const active =
                item.href === "/admin"
                  ? pathname === "/admin"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className="flex items-center gap-2.5 rounded-sm px-2.5 py-2 text-[14px] no-underline transition-colors duration-150"
                  style={{
                    background: active ? "var(--color-accent-pale)" : undefined,
                    color: active
                      ? "var(--color-accent)"
                      : "var(--color-ink-soft)",
                    fontWeight: active ? 600 : 500,
                  }}
                >
                  <Icon
                    className="h-4 w-4 flex-shrink-0"
                    strokeWidth={2}
                    style={{
                      color: active
                        ? "var(--color-accent)"
                        : "var(--color-ink-faint)",
                    }}
                  />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto border-t border-rule p-3">
            <Link
              href="/review"
              className="text-[12.5px] text-ink-mute no-underline transition-colors hover:text-ink"
            >
              ← ARBITRA&apos;ya dön
            </Link>
          </div>
        </aside>

        {/* İçerik */}
        <main
          className="min-w-0 flex-1 overflow-y-auto"
          style={{ height: "100vh" }}
        >
          <div className="mx-auto max-w-[1100px] px-6 py-8 md:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
