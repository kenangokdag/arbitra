"use client";

/**
 * ReviewOnboardingTour — 4 adımlı, statik içerikli ilk-giriş turu.
 * REVIEW_ONBOARDING_TURU_2026-08-17.
 *
 * Neden statik modal, in-context spotlight DEĞİL (plan §2): adımların
 * çoğu FARKLI sayfalara ait (upload vs. rapor) ve rapor sayfasındaki gerçek
 * elemanlar (öncelikli liste, sınırlayıcı boyut) SADECE bir rapor işlendikten
 * SONRA var olur — "ilk giriş"te (henüz hiçbir şey yüklenmemişken) gerçek
 * elemanlara işaret etmek mümkün değil.
 *
 * A11y: ConfirmDialog.tsx'in (web/src/components/ui/) deseniyle TUTARLI —
 * role=dialog + aria-modal + aria-labelledby + Escape + Tab focus-trap +
 * focus-restore. Paylaşılan bir Dialog primitive'i YOK (plan §1, bilinçli
 * kapsam-dışı) — bu bileşen kendi a11y'sini AnchorDrawer/ConfirmDialog gibi
 * kendi içinde yazar.
 *
 * Kapanış deseni: Atla / Escape / backdrop-click / son adımda "Anladım" —
 * HEPSİ markReviewTourSeen() çağırır (herhangi bir kapanış = kullanıcı
 * kararını verdi, bir daha göstermeyiz).
 */

import { useEffect, useId, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Sparkles, X } from "lucide-react";

type Step = {
  title: string;
  body: string;
};

// Adım 1 metni: api/services/review_orchestration.py:62-66'daki
// _ETHICS_NOTICE_EDITOR sabitine YAKIN — bilinçli küçük tekrar (plan §1,
// hukuki/etik metin nadiren değişir, sync-drift riski düşük).
const STEPS: Step[] = [
  {
    title: "Editör modunda sorumluluk sende",
    body:
      "Editör modunu seçtiğinde, incelediğin makale büyük ihtimalle başkasına " +
      "ait ve henüz yayımlanmamış olabilir. Bu otomatik değerlendirme YOL " +
      "GÖSTERİCİDİR; insan hakemin ve editör kararının yerine geçmez. " +
      "Gizlilik sorumluluğu sende — makaleyi üçüncü kişilerle paylaşma.",
  },
  {
    title: "Yükleme akışı",
    body:
      "Word, PDF, LaTeX ya da ZIP yükle → değerlendirme türünü (yazar/editör) " +
      "ve dili seç → gizlilik ayarlarını gözden geçir. Motor atıf bütünlüğü, " +
      "kapsam ve istatistik kontrollerini deterministik yapar; yorum ve karar " +
      "çok-personalı bir hakem paneliyle üretilir.",
  },
  {
    title: "Rapor sayfasında yeni: önceliklendirilmiş yol haritası",
    body:
      "Rapor artık üç yeni şey gösteriyor: önce ne yapman gerektiğini " +
      "sıralayan bir düzeltme listesi (P0/P1/P2), seni en çok geride tutan " +
      "boyutu somut gerekçesiyle vurgulayan bir kutu, ve her kararın yanında " +
      "ne kadar güvenilir olduğunu gösteren bir güven göstergesi.",
  },
  {
    title: "Danışman panelin hazır",
    body:
      "Sağ üstteki Danışman panelinden istediğin an soru sorabilirsin. " +
      "Bulunduğun sayfanın bağlamına göre yardımcı olur.",
  },
];

export function ReviewOnboardingTour({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0);
  const titleId = useId();
  const descId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const isLast = step === STEPS.length - 1;
  const isFirst = step === 0;

  // Odağı yönet: açılışta içeri al, kapanışta tetikleyiciye iade.
  useEffect(() => {
    triggerRef.current = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => closeBtnRef.current?.focus(), 50);
    return () => {
      window.clearTimeout(t);
      triggerRef.current?.focus?.();
    };
  }, []);

  // Esc kapatır + Tab focus-trap.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusables = dialogRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (!first || !last) return;
        const active = document.activeElement;
        if (e.shiftKey && active === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const current = STEPS[step]!;

  return (
    <div
      data-testid="review-onboarding-tour"
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{
        background: "color-mix(in oklab, var(--color-ink) 55%, transparent)",
        backdropFilter: "blur(8px)",
      }}
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        className="relative w-full max-w-md overflow-hidden rounded-xl border"
        style={{
          background: "var(--color-bg-card)",
          color: "var(--color-ink)",
          borderColor: "var(--color-rule)",
          boxShadow: "var(--shadow-lg)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          ref={closeBtnRef}
          type="button"
          onClick={onClose}
          aria-label="Turu kapat"
          data-testid="review-onboarding-tour-close"
          className="absolute right-4 top-4 z-10 flex h-8 w-8 items-center justify-center rounded-lg text-ink-faint transition-colors hover:bg-bg-hover hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="p-7">
          <div className="mb-4 flex items-start gap-3">
            <div
              className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl"
              style={{ background: "var(--color-accent-pale)" }}
            >
              <Sparkles className="h-5 w-5" style={{ color: "var(--color-accent)" }} aria-hidden />
            </div>
            <div className="min-w-0 pt-0.5">
              <span className="font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-ink-faint">
                Adım {step + 1} / {STEPS.length}
              </span>
              <h2
                id={titleId}
                className="font-display text-lg font-semibold italic leading-tight text-ink"
              >
                {current.title}
              </h2>
            </div>
          </div>

          <p id={descId} className="mb-6 text-sm leading-relaxed text-ink-soft">
            {current.body}
          </p>

          {/* adım noktaları */}
          <div className="mb-5 flex items-center justify-center gap-1.5">
            {STEPS.map((s, i) => (
              <span
                key={s.title}
                aria-hidden
                className="h-1.5 rounded-full transition-all"
                style={{
                  width: i === step ? "16px" : "6px",
                  background: i === step ? "var(--color-accent)" : "var(--color-rule)",
                }}
              />
            ))}
          </div>

          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={onClose}
              data-testid="review-onboarding-tour-skip"
              className="rounded-md px-3 py-2 text-sm font-medium text-ink-mute transition-colors hover:bg-bg-soft"
            >
              Atla
            </button>
            <div className="flex items-center gap-2">
              {!isFirst ? (
                <button
                  type="button"
                  onClick={() => setStep((s) => Math.max(0, s - 1))}
                  data-testid="review-onboarding-tour-back"
                  className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-bg-soft"
                >
                  <ChevronLeft className="h-4 w-4" aria-hidden />
                  Geri
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => (isLast ? onClose() : setStep((s) => s + 1))}
                data-testid="review-onboarding-tour-next"
                className="inline-flex items-center gap-1 rounded-md px-4 py-2 text-sm font-semibold transition-opacity"
                style={{ background: "var(--color-accent)", color: "var(--color-accent-fg)" }}
              >
                {isLast ? "Anladım" : "İleri"}
                {!isLast ? <ChevronRight className="h-4 w-4" aria-hidden /> : null}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
