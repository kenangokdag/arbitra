"use client";

/**
 * ConfirmDialog — erişilebilir, yıkıcı-eylem onay diyaloğu.
 *
 * A11y: role="dialog" + aria-modal + aria-labelledby + Escape + focus-trap +
 *       focus-restore (WaitlistModal.tsx deseni — kaynak tek a11y çıpası).
 * Lifecycle (madde 13 — yıkıcı eylem): idle → submitting (çift-gönderim kilidi +
 *       spinner) → success (kısa onay) → onSuccess; veya error (okunur Türkçe,
 *       tekrar dene). Gönderim/başarı sırasında diyalog KİLİTLİ (Esc/backdrop
 *       kapatmaz) — yarıda kalan yıkıcı işlem yok.
 * Opsiyonel `confirmPhrase`: kullanıcı metni BİREBİR yazana kadar onay butonu
 *       pasif (typed-confirmation gate).
 * Renk: yıkıcı eylem = var(--color-warn) (icat kırmızı DEĞİL — design tokens).
 */

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, Loader2, X, type LucideIcon } from "lucide-react";

import { ApiError } from "@/lib/api";

/** ApiError → okunur Türkçe (ham JSON değil). Çağıran override edebilir. */
export function defaultErrorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 400) return "Onay metni eşleşmedi. Lütfen tam olarak yazın.";
    if (e.status === 401) return "Oturumun sona ermiş görünüyor. Lütfen tekrar giriş yap.";
    if (e.status === 403) return "Bu işlem için yetkin yok.";
    if (e.status === 404)
      return "Kayıt bulunamadı — daha önce silinmiş ya da sana ait olmayabilir.";
    if (e.status >= 500)
      return "Sunucuda bir sorun oluştu. Lütfen biraz sonra tekrar dene.";
    return `İşlem tamamlanamadı (HTTP ${e.status}). Lütfen tekrar dene.`;
  }
  if (e instanceof Error) {
    // Ağ/fetch hatası (TypeError: Failed to fetch vb.)
    return "Bağlantı kurulamadı. İnternet bağlantını kontrol edip tekrar dene.";
  }
  return "Beklenmeyen bir hata oluştu. Lütfen tekrar dene.";
}

type Phase = "idle" | "submitting" | "success";

type ConfirmDialogProps = {
  open: boolean;
  onClose: () => void;
  /** Asıl işlem. Başarısızlıkta THROW etmeli (ApiError). */
  onConfirm: () => Promise<void>;
  /** Başarı (ve varsa kısa başarı görünümü) sonrası — yönlendirme burada yapılır. */
  onSuccess?: () => void;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  /** Verilirse kullanıcı bu metni BİREBİR yazana kadar onay pasif. */
  confirmPhrase?: string;
  /** Yazım kutusunun üstündeki kısa etiket (confirmPhrase verildiğinde). */
  phraseLabel?: ReactNode;
  icon?: LucideIcon;
  /** Verilirse başarıda ~1.2sn gösterilir, sonra onSuccess çağrılır. */
  success?: { title: string; description: ReactNode };
  /** ApiError → metin override. Yoksa defaultErrorMessage. */
  formatError?: (e: unknown) => string;
};

const SUCCESS_HOLD_MS = 1200;

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  onSuccess,
  title,
  description,
  confirmLabel,
  cancelLabel = "Vazgeç",
  confirmPhrase,
  phraseLabel,
  icon: Icon = AlertTriangle,
  success,
  formatError = defaultErrorMessage,
}: ConfirmDialogProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [typed, setTyped] = useState("");

  const titleId = useId();
  const descId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const initialFocusRef = useRef<HTMLInputElement | HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const locked = phase !== "idle"; // submitting | success → kapatma kilidi

  // Açılışta state sıfırla — render-fazı "prop değişince state ayarla" deseni
  // (React docs; effect-içi setState'ten kaçınır, cascading render yok).
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) {
      setPhase("idle");
      setError(null);
      setTyped("");
    }
  }

  // Odağı yönet: açılışta içeri al, kapanışta tetikleyiciye iade (focus-restore).
  useEffect(() => {
    if (!open) return;
    triggerRef.current = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => initialFocusRef.current?.focus(), 50);
    return () => {
      window.clearTimeout(t);
      triggerRef.current?.focus?.();
    };
  }, [open]);

  // Esc kapatır (kilitli değilse) + Tab focus-trap.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (!locked) onClose();
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
  }, [open, locked, onClose]);

  const phraseRequired = typeof confirmPhrase === "string" && confirmPhrase.length > 0;
  const phraseMatches = !phraseRequired || typed === confirmPhrase;

  const handleConfirm = useCallback(async () => {
    if (phase === "submitting") return; // çift-gönderim kilidi
    if (!phraseMatches) return; // typed-confirmation gate
    setPhase("submitting");
    setError(null);
    try {
      await onConfirm();
      if (success) {
        setPhase("success");
        window.setTimeout(() => onSuccess?.(), SUCCESS_HOLD_MS);
      } else {
        // Başarı görünümü yoksa doğrudan devral (genelde yönlendirme → unmount).
        onSuccess?.();
      }
    } catch (e) {
      setPhase("idle");
      setError(formatError(e));
    }
  }, [phase, phraseMatches, onConfirm, success, onSuccess, formatError]);

  if (!open) return null;

  const warn = "var(--color-warn)";

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{
        background: "color-mix(in oklab, var(--color-ink) 55%, transparent)",
        backdropFilter: "blur(8px)",
        animation: "fadeIn 0.2s ease-out",
      }}
      onClick={() => {
        if (!locked) onClose();
      }}
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
          animation: "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Kapat — gönderim/başarı sırasında gizli (kilitli) */}
        {!locked && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="absolute right-4 top-4 z-10 flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-ink-faint)] transition-colors hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-ink)]"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        <div className="p-7">
          {phase === "success" && success ? (
            <div className="text-center" role="status" aria-live="polite">
              <div
                className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl"
                style={{ background: "var(--color-ok-pale)" }}
              >
                <Loader2
                  className="h-6 w-6 animate-spin motion-reduce:hidden"
                  style={{ color: "var(--color-ok)" }}
                  aria-hidden
                />
              </div>
              <h2
                id={titleId}
                className="font-display mb-2 text-xl font-semibold italic text-[var(--color-ink)]"
              >
                {success.title}
              </h2>
              <p id={descId} className="text-sm text-[var(--color-ink-soft)]">
                {success.description}
              </p>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-start gap-3">
                <div
                  className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl"
                  style={{ background: "var(--color-warn-pale)" }}
                >
                  <Icon className="h-5 w-5" style={{ color: warn }} strokeWidth={2} aria-hidden />
                </div>
                <div className="min-w-0 pt-0.5">
                  <h2
                    id={titleId}
                    className="font-display text-lg font-semibold italic leading-tight text-[var(--color-ink)]"
                  >
                    {title}
                  </h2>
                </div>
              </div>

              <div id={descId} className="mb-4 text-sm leading-relaxed text-[var(--color-ink-soft)]">
                {description}
              </div>

              {phraseRequired && (
                <label className="mb-4 block">
                  <span className="mb-1.5 block text-xs font-medium text-[var(--color-ink-soft)]">
                    {phraseLabel ?? (
                      <>
                        Onaylamak için{" "}
                        <span className="font-mono font-semibold text-[var(--color-ink)]">
                          {confirmPhrase}
                        </span>{" "}
                        yazın
                      </>
                    )}
                  </span>
                  <input
                    ref={initialFocusRef as React.RefObject<HTMLInputElement>}
                    type="text"
                    value={typed}
                    onChange={(e) => setTyped(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && phraseMatches) {
                        e.preventDefault();
                        void handleConfirm();
                      }
                    }}
                    disabled={phase === "submitting"}
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck={false}
                    aria-label={typeof confirmPhrase === "string" ? `Onay metni: ${confirmPhrase}` : "Onay metni"}
                    className="w-full rounded-md border px-3 py-2.5 font-mono text-sm outline-none transition-colors focus:ring-2"
                    style={{
                      background: "var(--color-bg-card)",
                      color: "var(--color-ink)",
                      borderColor: phraseMatches && typed.length > 0 ? warn : "var(--color-rule)",
                    }}
                  />
                </label>
              )}

              {error && (
                <div
                  role="alert"
                  className="mb-4 rounded-md border px-3 py-2 text-xs"
                  style={{
                    color: "var(--color-danger)",
                    borderColor: "color-mix(in oklab, var(--color-danger) 30%, transparent)",
                    background: "var(--color-danger-pale)",
                  }}
                >
                  {error}
                </div>
              )}

              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={phase === "submitting"}
                  className="rounded-md px-4 py-2.5 text-sm font-medium text-[var(--color-ink-soft)] transition-colors hover:bg-[var(--color-bg-soft)] disabled:cursor-not-allowed disabled:opacity-50"
                  style={{ border: "1px solid var(--color-rule)" }}
                >
                  {cancelLabel}
                </button>
                <button
                  ref={!phraseRequired ? (initialFocusRef as React.RefObject<HTMLButtonElement>) : undefined}
                  type="button"
                  onClick={() => void handleConfirm()}
                  disabled={phase === "submitting" || !phraseMatches}
                  className="inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
                  style={{ background: warn, color: "var(--color-accent-fg)" }}
                >
                  {phase === "submitting" ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      İşleniyor…
                    </>
                  ) : (
                    confirmLabel
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
