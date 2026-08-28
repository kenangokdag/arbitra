"use client";

/* ============================================================
   ARBITRA — Örnek rapor (public sample review report)
   ------------------------------------------------------------
   Amaç: Kayıt olmadan, prospect'in TAM hakemlik kokpitini (verdict →
   risk → kanıt-çıpası → uzman katmanı) gerçek tasarımıyla görmesi.
   REUSE: ReviewReportView (kokpit) + REPORT_V2_DEMO (güvenli fixture).
   DÜRÜSTLÜK: Sayfa boyunca KALICI "Örnek değerlendirme — illüstratif
   veri" rozeti + dipnot. Hiçbir sayı/yargı gerçek kullanıcı verisi
   değildir; uydurma metrik gerçekmiş gibi sunulmaz.
   Marka kabuğu landing ile aynı token sistemi (var(--color-*)).
   ============================================================ */

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";

import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";
import { ReviewReportView } from "@/components/review/ReviewReportView";
import { WaitlistModal } from "@/components/marketing/WaitlistModal";
import { REPORT_V2_DEMO } from "@/fixtures/report-v2-demo";
import { BRAND } from "@/lib/brand";
import type { WaitlistSource } from "@/lib/waitlist-api";

/* Tek aksan token'ı — landing ile aynı kaynak (globals @theme). */
const ACCENT = "var(--color-accent)";

/* KALICI dürüstlük rozeti — sayfanın yapışkan başlığında her zaman görünür. */
function SampleBadge() {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-sans text-[10.5px] font-medium uppercase tracking-[0.1em]"
      style={{
        color: "var(--color-ink-faint)",
        borderColor: "color-mix(in oklab, var(--color-accent) 45%, var(--color-rule))",
        background: "var(--color-accent-pale)",
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: ACCENT }} />
      Örnek değerlendirme — illüstratif veri
    </span>
  );
}

export default function SampleReportPage() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [waitlistSource, setWaitlistSource] =
    useState<WaitlistSource>("landing_hero");

  const openWaitlist = (source: WaitlistSource) => {
    setWaitlistSource(source);
    setWaitlistOpen(true);
  };

  return (
    <>
      <main
        className="font-display"
        style={{
          background: "var(--color-bg)",
          color: "var(--color-ink-soft)",
        }}
      >
        {/* Yapışkan marka kabuğu — KALICI rozet burada (kaydırırken kaybolmaz). */}
        <header
          className="sticky top-0 z-50 border-b backdrop-blur"
          style={{
            background: "color-mix(in oklab, var(--color-bg) 92%, transparent)",
            borderColor: "var(--color-rule-soft)",
          }}
        >
          <div className="mx-auto flex h-[64px] max-w-[1080px] items-center justify-between gap-4 px-5 md:px-8">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2.5">
                <ArbitraWordmark size="md" />
              </Link>
              <Link
                href="/"
                className="hidden items-center gap-1.5 text-[13px] font-medium text-[var(--color-ink-faint)] transition hover:text-[var(--color-ink)] sm:inline-flex"
              >
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
                Tanıtıma dön
              </Link>
            </div>
            <SampleBadge />
          </div>
        </header>

        {/* Giriş şeridi — tek cümle + üst CTA. */}
        <section className="border-b" style={{ borderColor: "var(--color-rule-soft)" }}>
          <div className="mx-auto max-w-[1080px] px-5 py-10 md:px-8 md:py-12">
            <h1
              className="font-display font-medium text-[var(--color-ink)]"
              style={{
                fontSize: "clamp(26px, 3.4vw, 38px)",
                letterSpacing: "-0.018em",
                lineHeight: 1.12,
              }}
            >
              Gerçek bir Arbitra değerlendirmesi —{" "}
              <em className="font-crimson italic" style={{ color: ACCENT }}>
                örnek makale üzerinde.
              </em>
            </h1>
            <p
              className="mt-3.5 max-w-[58ch] font-display text-[16.5px] leading-[1.55] text-[var(--color-ink-soft)]"
            >
              Aşağıdaki kokpit, {BRAND}&apos;nın bir hakem raporunu birebir
              gösterir: önerilen karar, risklerin metnindeki cümleye çıpalı
              kanıtı ve uzman katmanı. Tüm veriler kurgusal bir örnek makaleye
              aittir.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => openWaitlist("landing_hero")}
                className="inline-flex h-[46px] items-center gap-2 rounded-md bg-[var(--color-ink)] px-5 text-[14.5px] font-medium text-[var(--color-bg)] transition hover:opacity-90 active:translate-y-px"
              >
                Kendi makaleni değerlendir → Waitlist
                <ArrowRight className="h-4 w-4" />
              </button>
              <Link
                href="/#nasil-calisir"
                className="text-[13.5px] font-medium text-[var(--color-ink-faint)] underline-offset-4 transition hover:text-[var(--color-ink)] hover:underline"
              >
                Nasıl çalışır?
              </Link>
            </div>
          </div>
        </section>

        {/* KOKPİT — gerçek ReviewReportView, güvenli fixture ile. Anchor drawer,
            katman aç/kapa interaktif çalışır (statik veri, fetch yok). */}
        <section className="mx-auto max-w-[1080px] px-5 py-12 md:px-8 md:py-16">
          <ReviewReportView report={REPORT_V2_DEMO} jobId="ornek" />
        </section>

        {/* Alt CTA + dürüstlük dipnotu. */}
        <section
          className="border-t py-20 text-center md:py-24"
          style={{
            borderColor: "var(--color-rule-soft)",
            background: "var(--color-ink)",
          }}
        >
          <div className="mx-auto max-w-[720px] px-6">
            <h2
              className="mx-auto font-display font-medium"
              style={{
                fontSize: "clamp(28px, 4vw, 44px)",
                letterSpacing: "-0.02em",
                lineHeight: 1.1,
                color: "var(--color-bg)",
                marginBottom: 18,
              }}
            >
              Sıradaki rapor{" "}
              <em
                className="font-crimson italic"
                style={{ color: "var(--color-accent-soft)" }}
              >
                senin makalen olsun.
              </em>
            </h2>
            <p
              className="mx-auto font-display text-[17px] leading-[1.55]"
              style={{
                color: "color-mix(in oklab, var(--color-bg) 78%, transparent)",
                maxWidth: "48ch",
                marginBottom: 28,
              }}
            >
              {BRAND} lansman öncesi. Erken erişim listesine katıl; hazır
              olduğunda kendi makaleni üç bağımsız hakemin önüne çıkar.
            </p>
            <button
              type="button"
              onClick={() => openWaitlist("landing_pricing")}
              className="inline-flex h-[50px] items-center gap-2 rounded-md px-6 font-sans text-[15px] font-medium transition hover:opacity-90 active:translate-y-px"
              style={{ background: ACCENT, color: "var(--color-accent-fg)" }}
            >
              Kendi makaleni değerlendir → Waitlist
              <ArrowRight className="h-4 w-4" />
            </button>

            <p
              className="mx-auto mt-10 max-w-[52ch] font-sans text-[12.5px] leading-relaxed"
              style={{ color: "color-mix(in oklab, var(--color-bg) 55%, transparent)" }}
            >
              Bu rapor örnek bir makale içindir; gerçek kullanıcı verisi
              değildir. Tüm yargılar, skorlar ve çıpalar yalnızca {BRAND}
              kokpitinin nasıl göründüğünü göstermek için kurgulanmıştır.
            </p>
          </div>
        </section>
      </main>

      <WaitlistModal
        open={waitlistOpen}
        source={waitlistSource}
        onClose={() => setWaitlistOpen(false)}
      />
    </>
  );
}
