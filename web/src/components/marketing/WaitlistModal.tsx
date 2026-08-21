"use client";

/**
 * V1-S4 WaitlistModal — Landing capture form (Scope A — Minimal).
 *
 * kaynak: docs/plans/V1_S4_waitlist_capture.md §3 (V1-S4-02)
 * Stil: landing token sistemi (var(--color-*)) — gradyan/glow/parıltı YOK
 *       (DESIGN-DECISIONS-LANDING §6/§8). Tek aksan = var(--color-accent).
 * A11y: role="dialog" + aria-modal + aria-labelledby + Escape + focus-trap +
 *       focus-restore (AnchorDrawer deseni — ReviewReportView.tsx).
 * Anti-spam: honeypot field (display:none + aria-hidden + tabIndex=-1).
 * KVKK consent YOK (Scope A — KD-V1-S4-05).
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { BRAND } from "@/lib/brand";
import { Check, Mail, Sparkles, X } from "lucide-react";
import { submitWaitlist, type WaitlistSource } from "@/lib/waitlist-api";

type Props = {
  open: boolean;
  source: WaitlistSource;
  onClose: () => void;
};

type Status = "idle" | "loading" | "success" | "duplicate" | "error";

const TITLE_ID = "waitlist-modal-title";

export function WaitlistModal({ open, source, onClose }: Props) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [website, setWebsite] = useState(""); // honeypot
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const emailRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const handleClose = useCallback(() => {
    setEmail("");
    setName("");
    setWebsite("");
    setStatus("idle");
    setErrorMsg("");
    onClose();
  }, [onClose]);

  // açılış: tetikleyiciyi sakla + odağı içeri al; kapanışta odağı tetikleyiciye
  // iade et (WCAG 2.2 AA — AnchorDrawer deseni). Form state'i her kapanışta
  // handleClose sıfırlar → açılışta setState gereksiz (set-state-in-effect'ten kaçınılır).
  useEffect(() => {
    if (!open) return;
    triggerRef.current = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => {
      (emailRef.current ?? closeBtnRef.current)?.focus();
    }, 50);
    return () => {
      window.clearTimeout(t);
      triggerRef.current?.focus?.();
    };
  }, [open]);

  // Esc kapatır + Tab focus-trap (odak dialog içinde döner, arka plana kaçmaz)
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose();
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
  }, [open, handleClose]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (status === "loading") return;
    setStatus("loading");
    setErrorMsg("");

    const result = await submitWaitlist({
      email: email.trim(),
      name: name.trim(),
      source,
      website,
    });

    if (result.kind === "success") {
      setStatus("success");
    } else if (result.kind === "duplicate") {
      setStatus("duplicate");
    } else {
      setStatus("error");
      setErrorMsg(result.message);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{
        background: "color-mix(in oklab, var(--color-ink) 55%, transparent)",
        backdropFilter: "blur(8px)",
        animation: "fadeIn 0.2s ease-out",
      }}
      onClick={handleClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={TITLE_ID}
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
        <button
          ref={closeBtnRef}
          onClick={handleClose}
          aria-label="Kapat"
          className="absolute right-4 top-4 z-10 flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-ink-faint)] transition-colors hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-ink)]"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="p-8">
          {status === "success" ? (
            <SuccessView onClose={handleClose} />
          ) : status === "duplicate" ? (
            <DuplicateView email={email} onClose={handleClose} />
          ) : (
            <FormView
              emailRef={emailRef}
              email={email}
              setEmail={setEmail}
              name={name}
              setName={setName}
              website={website}
              setWebsite={setWebsite}
              onSubmit={handleSubmit}
              status={status}
              errorMsg={errorMsg}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function FormView({
  emailRef,
  email,
  setEmail,
  name,
  setName,
  website,
  setWebsite,
  onSubmit,
  status,
  errorMsg,
}: {
  emailRef: React.RefObject<HTMLInputElement | null>;
  email: string;
  setEmail: (v: string) => void;
  name: string;
  setName: (v: string) => void;
  website: string;
  setWebsite: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  status: Status;
  errorMsg: string;
}) {
  return (
    <form onSubmit={onSubmit}>
      <div className="mb-5 flex items-center gap-3">
        <div
          className="flex h-12 w-12 items-center justify-center rounded-xl"
          style={{ background: "var(--color-accent-pale)" }}
        >
          <Mail className="h-5 w-5" style={{ color: "var(--color-accent)" }} strokeWidth={2} />
        </div>
        <div>
          <h2
            id={TITLE_ID}
            className="font-display text-xl font-semibold italic leading-tight text-[var(--color-ink)]"
          >
            Erken erişim listesi
          </h2>
          <p className="text-xs text-[var(--color-ink-faint)]">
            {BRAND} hazır olduğunda ilk siz haberdar olun
          </p>
        </div>
      </div>

      <label className="mb-3 block">
        <span className="mb-1 block text-xs font-medium text-[var(--color-ink-soft)]">Ad Soyad</span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          minLength={2}
          maxLength={100}
          placeholder="Ada Lovelace"
          className="w-full rounded-md border border-[var(--color-rule)] px-3 py-2.5 text-sm outline-none transition-colors focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent-pale)]"
          style={{ background: "var(--color-bg-card)", color: "var(--color-ink)" }}
        />
      </label>

      <label className="mb-4 block">
        <span className="mb-1 block text-xs font-medium text-[var(--color-ink-soft)]">E-posta</span>
        <input
          ref={emailRef}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={254}
          placeholder="ornek@universite.edu.tr"
          className="w-full rounded-md border border-[var(--color-rule)] px-3 py-2.5 text-sm outline-none transition-colors focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent-pale)]"
          style={{ background: "var(--color-bg-card)", color: "var(--color-ink)" }}
        />
      </label>

      {/* Honeypot — gerçek kullanıcı görmez (display:none + aria-hidden + tabIndex=-1). */}
      <div aria-hidden="true" style={{ position: "absolute", left: "-9999px", top: "-9999px" }}>
        <label>
          Web sitesi (boş bırakın)
          <input
            type="text"
            tabIndex={-1}
            autoComplete="off"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />
        </label>
      </div>

      {status === "error" && errorMsg && (
        <div
          className="mb-3 rounded-md border px-3 py-2 text-xs"
          style={{
            color: "var(--color-danger)",
            borderColor: "color-mix(in oklab, var(--color-danger) 30%, transparent)",
            background: "var(--color-danger-pale)",
          }}
        >
          {errorMsg}
        </div>
      )}

      <button
        type="submit"
        disabled={status === "loading"}
        className="flex w-full items-center justify-center gap-2 rounded-md py-3 font-medium transition active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
        style={{ background: "var(--color-ink)", color: "var(--color-accent-fg)" }}
      >
        {status === "loading" ? "Gönderiliyor..." : "Listeye katıl"}
      </button>

      <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-[11px] text-[var(--color-ink-faint)]">
        <Sparkles className="h-3 w-3" />
        Spam yok — sadece lansman duyurusu
      </p>
    </form>
  );
}

function SuccessView({ onClose }: { onClose: () => void }) {
  return (
    <div className="text-center">
      <div
        className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl"
        style={{ background: "var(--color-ok-pale)" }}
      >
        <Check className="h-7 w-7" style={{ color: "var(--color-ok)" }} strokeWidth={3} />
      </div>
      <h2 id={TITLE_ID} className="font-display mb-2 text-xl font-semibold italic text-[var(--color-ink)]">
        Listedesiniz
      </h2>
      <p className="mb-6 text-sm text-[var(--color-ink-soft)]">
        {BRAND} erken erişim açıldığında size e-posta atacağız.
      </p>
      <button
        onClick={onClose}
        className="w-full rounded-md py-2.5 text-sm font-medium text-[var(--color-ink)] transition-colors hover:bg-[var(--color-bg-hover)]"
        style={{ background: "var(--color-bg-soft)" }}
      >
        Kapat
      </button>
    </div>
  );
}

function DuplicateView({ email, onClose }: { email: string; onClose: () => void }) {
  return (
    <div className="text-center">
      <div
        className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl"
        style={{ background: "var(--color-accent-pale)" }}
      >
        <Mail className="h-7 w-7" style={{ color: "var(--color-accent)" }} strokeWidth={2.5} />
      </div>
      <h2 id={TITLE_ID} className="font-display mb-2 text-xl font-semibold italic text-[var(--color-ink)]">
        Zaten listemizdesiniz
      </h2>
      <p className="mb-6 text-sm text-[var(--color-ink-soft)]">
        <span className="font-medium text-[var(--color-ink)]">{email}</span> kayıtlı. Lansman duyurusunu bekleyin.
      </p>
      <button
        onClick={onClose}
        className="w-full rounded-md py-2.5 text-sm font-medium text-[var(--color-ink)] transition-colors hover:bg-[var(--color-bg-hover)]"
        style={{ background: "var(--color-bg-soft)" }}
      >
        Kapat
      </button>
    </div>
  );
}
