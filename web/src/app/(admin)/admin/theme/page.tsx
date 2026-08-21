// FAZ 4B — Global tema yönetimi. Admin renk+font seçer, CANLI verdict-kart
// önizlemesinde sonucu görür, WCAG kontrastı dürüstçe okur, kaydeder.
// 5 durum: idle / loading / success / error + alan doğrulama + çift-submit kilidi.
// Yetkisiz (PATCH 403) → net mesaj, beyaz ekran değil.

"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  Loader2,
  RotateCcw,
  ShieldAlert,
} from "lucide-react";

import { useTheme, useUpdateTheme } from "@/hooks/useReview";
import { ApiError } from "@/lib/api";
import type {
  FontSansKey,
  FontSerifKey,
  ThemeUpdate,
} from "@/lib/review-api";
import {
  FONT_SANS_LABELS,
  FONT_SANS_MAP,
  FONT_SERIF_LABELS,
  FONT_SERIF_MAP,
  contrastRatio,
  isHexColor,
  WCAG_AA_TEXT,
  WCAG_AA_UI,
} from "@/lib/theme";

const FONT_SANS_KEYS = Object.keys(FONT_SANS_LABELS) as FontSansKey[];
const FONT_SERIF_KEYS = Object.keys(FONT_SERIF_LABELS) as FontSerifKey[];

export default function AdminThemePage() {
  const theme = useTheme();
  const update = useUpdateTheme();

  // Form alanları — tema yüklenince tek sefer seed edilir.
  const [accent, setAccent] = useState("#4F46E5");
  const [bg, setBg] = useState("#f8fafc");
  const [ink, setInk] = useState("#0f172a");
  const [fontSans, setFontSans] = useState<FontSansKey>("inter");
  const [fontSerif, setFontSerif] = useState<FontSerifKey>("lora");
  const seeded = useRef(false);

  useEffect(() => {
    if (!theme.data || seeded.current) return;
    setAccent(theme.data.accent_color);
    setBg(theme.data.bg_color);
    setInk(theme.data.ink_color);
    setFontSans(theme.data.font_sans);
    setFontSerif(theme.data.font_serif);
    seeded.current = true;
  }, [theme.data]);

  const accentValid = isHexColor(accent);
  const bgValid = isHexColor(bg);
  const inkValid = isHexColor(ink);
  const allValid = accentValid && bgValid && inkValid;

  const resetToSaved = () => {
    if (!theme.data) return;
    setAccent(theme.data.accent_color);
    setBg(theme.data.bg_color);
    setInk(theme.data.ink_color);
    setFontSans(theme.data.font_sans);
    setFontSerif(theme.data.font_serif);
    update.reset();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (update.isPending || !allValid) return; // çift-submit + geçersiz kilidi
    const body: ThemeUpdate = {
      accent_color: accent,
      bg_color: bg,
      ink_color: ink,
      font_sans: fontSans,
      font_serif: fontSerif,
    };
    update.mutate(body);
  };

  const unauthorized =
    update.isError &&
    update.error instanceof ApiError &&
    update.error.status === 403;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1.5">
        <h1 className="serif text-[28px] font-medium italic leading-tight tracking-[-0.015em]">
          Tema
        </h1>
        <p className="max-w-2xl text-[14px] text-ink-mute">
          ARBITRA&apos;nın küresel görünümü: vurgu rengi, zemin, mürekkep ve yazı
          tipleri. Değişiklik kaydedilince tüm kullanıcılara uygulanır. Sağdaki
          önizleme seçimlerinizi canlı gösterir.
        </p>
      </header>

      {theme.isError ? (
        <ErrorBox
          message={theme.error.message}
          onRetry={() => void theme.refetch()}
        />
      ) : theme.isPending ? (
        <LoadingSkeleton />
      ) : (
        <form
          onSubmit={handleSubmit}
          className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,360px)]"
        >
          {/* SOL — kontroller */}
          <div className="flex flex-col gap-5">
            <fieldset
              disabled={update.isPending}
              className="flex flex-col gap-4 disabled:opacity-60"
            >
              <ColorField
                id="accent"
                label="Vurgu rengi"
                hint="Bağlantı, buton ve aktif öğeler"
                value={accent}
                valid={accentValid}
                onChange={setAccent}
              />
              <ColorField
                id="bg"
                label="Zemin rengi"
                hint="Sayfa arka planı"
                value={bg}
                valid={bgValid}
                onChange={setBg}
              />
              <ColorField
                id="ink"
                label="Mürekkep (metin)"
                hint="Gövde metni rengi"
                value={ink}
                valid={inkValid}
                onChange={setInk}
              />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <SelectField
                  id="font-sans"
                  label="Gövde yazı tipi (sans)"
                  value={fontSans}
                  options={FONT_SANS_KEYS}
                  labels={FONT_SANS_LABELS}
                  onChange={(v) => setFontSans(v as FontSansKey)}
                />
                <SelectField
                  id="font-serif"
                  label="Başlık yazı tipi (serif)"
                  value={fontSerif}
                  options={FONT_SERIF_KEYS}
                  labels={FONT_SERIF_LABELS}
                  onChange={(v) => setFontSerif(v as FontSerifKey)}
                />
              </div>
            </fieldset>

            {/* WCAG kontrast — dürüstlük okuması */}
            <div className="flex flex-col gap-2.5 rounded-md border border-rule-soft bg-bg-card p-4">
              <h2 className="font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-ink-faint">
                Erişilebilirlik · WCAG kontrast
              </h2>
              <ContrastRow
                label="Metin / Zemin"
                fg={ink}
                bg={bg}
                threshold={WCAG_AA_TEXT}
                requirement="AA metin ≥ 4.5"
              />
              <ContrastRow
                label="Vurgu / Zemin"
                fg={accent}
                bg={bg}
                threshold={WCAG_AA_UI}
                requirement="AA arayüz ≥ 3.0"
              />
            </div>

            {/* Kaydet + durum geri-bildirimi (5 durum) */}
            <div className="flex flex-col gap-3">
              {unauthorized ? (
                <StatusBanner
                  tone="danger"
                  icon={<ShieldAlert className="h-4 w-4" aria-hidden />}
                  title="Bu sayfa yöneticilere özel"
                  body="Temayı yalnızca yönetici hesapları kaydedebilir. Değişikliğiniz uygulanmadı."
                />
              ) : update.isError ? (
                <StatusBanner
                  tone="danger"
                  icon={<AlertTriangle className="h-4 w-4" aria-hidden />}
                  title="Kaydedilemedi"
                  body={update.error.message}
                />
              ) : update.isSuccess ? (
                <StatusBanner
                  tone="ok"
                  icon={<Check className="h-4 w-4" aria-hidden />}
                  title="Tema kaydedildi"
                  body="Yeni görünüm tüm kullanıcılara uygulandı."
                />
              ) : null}

              {!allValid ? (
                <p
                  role="alert"
                  className="text-[13px]"
                  style={{ color: "var(--color-danger)" }}
                >
                  Renkler #RRGGBB biçiminde olmalı (örn. #4F46E5). Geçersiz alanı
                  düzeltin.
                </p>
              ) : null}

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={update.isPending || !allValid}
                  className="inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-[14px] font-medium text-accent-fg transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
                  style={{ background: "var(--color-accent)" }}
                >
                  {update.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      Kaydediliyor…
                    </>
                  ) : (
                    "Temayı kaydet"
                  )}
                </button>
                <button
                  type="button"
                  onClick={resetToSaved}
                  disabled={update.isPending}
                  className="inline-flex items-center gap-1.5 rounded-md border border-rule px-3 py-2.5 text-[13px] font-medium text-ink-soft transition-colors hover:bg-bg-hover disabled:opacity-50"
                >
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden />
                  Kayıtlıya dön
                </button>
              </div>
            </div>
          </div>

          {/* SAĞ — CANLI önizleme (İMZA ANI) */}
          <div className="lg:sticky lg:top-8 lg:self-start">
            <ThemePreview
              accent={accentValid ? accent : "#4F46E5"}
              bg={bgValid ? bg : "#f8fafc"}
              ink={inkValid ? ink : "#0f172a"}
              fontSans={fontSans}
              fontSerif={fontSerif}
            />
          </div>
        </form>
      )}
    </div>
  );
}

// --- alt bileşenler --------------------------------------------------------

function ColorField({
  id,
  label,
  hint,
  value,
  valid,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  value: string;
  valid: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={`${id}-text`} className="flex flex-col gap-0.5">
        <span className="text-[13px] font-medium text-ink-soft">{label}</span>
        <span className="text-[12px] text-ink-faint">{hint}</span>
      </label>
      <div className="flex items-center gap-2.5">
        <input
          type="color"
          aria-label={`${label} renk seçici`}
          value={valid ? value.toLowerCase() : "#000000"}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 w-12 flex-shrink-0 cursor-pointer rounded-sm border border-rule bg-bg-card p-0.5"
        />
        <input
          id={`${id}-text`}
          type="text"
          inputMode="text"
          spellCheck={false}
          autoComplete="off"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#RRGGBB"
          aria-invalid={!valid}
          className="font-mono-pmid w-32 rounded-sm border bg-bg-input px-2.5 py-1.5 text-[13px] uppercase tracking-wide text-ink outline-none focus:ring-2 focus:ring-accent"
          style={{ borderColor: valid ? "var(--color-rule)" : "var(--color-danger)" }}
        />
      </div>
    </div>
  );
}

function SelectField({
  id,
  label,
  value,
  options,
  labels,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  labels: Record<string, string>;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-medium text-ink-soft">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-sm border border-rule bg-bg-input px-2.5 py-2 text-[13px] text-ink outline-none focus:ring-2 focus:ring-accent"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {labels[opt]}
          </option>
        ))}
      </select>
    </div>
  );
}

function ContrastRow({
  label,
  fg,
  bg,
  threshold,
  requirement,
}: {
  label: string;
  fg: string;
  bg: string;
  threshold: number;
  requirement: string;
}) {
  const ratio = contrastRatio(fg, bg);
  const known = ratio !== null;
  const pass = known && ratio >= threshold;
  const tone = !known
    ? "var(--color-ink-faint)"
    : pass
      ? "var(--color-ok)"
      : "var(--color-danger)";
  const pale = !known
    ? "var(--color-bg-soft)"
    : pass
      ? "var(--color-ok-pale)"
      : "var(--color-danger-pale)";

  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex flex-col">
        <span className="text-[13px] text-ink">{label}</span>
        <span className="text-[11px] text-ink-faint">{requirement}</span>
      </div>
      <span
        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium tabular-nums"
        style={{ background: pale, color: tone }}
      >
        <span className="font-mono-pmid">
          {known ? `${ratio.toFixed(2)}:1` : "—"}
        </span>
        <span aria-hidden>·</span>
        <span>{!known ? "geçersiz" : pass ? "geçer" : "zayıf"}</span>
      </span>
    </div>
  );
}

function ThemePreview({
  accent,
  bg,
  ink,
  fontSans,
  fontSerif,
}: {
  accent: string;
  bg: string;
  ink: string;
  fontSans: FontSansKey;
  fontSerif: FontSerifKey;
}) {
  return (
    <div className="flex flex-col gap-2">
      <span className="font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-ink-faint">
        Canlı önizleme
      </span>
      <div
        data-testid="theme-preview"
        className="overflow-hidden rounded-lg border border-rule shadow-sm"
        style={{ background: bg, color: ink, fontFamily: FONT_SANS_MAP[fontSans] }}
      >
        <div className="flex flex-col gap-3 p-5">
          <div className="flex items-center justify-between gap-2">
            <span
              className="text-[18px] font-medium italic leading-tight"
              style={{ fontFamily: FONT_SERIF_MAP[fontSerif] }}
            >
              Değerlendirme kararı
            </span>
            <span
              className="rounded-full px-2.5 py-1 text-[12px] font-semibold"
              style={{ background: accent, color: "#ffffff" }}
            >
              Büyük revizyon
            </span>
          </div>
          <p className="text-[13px] leading-relaxed" style={{ opacity: 0.85 }}>
            Çalışma güçlü bir araştırma sorusu sunuyor; ancak yöntem bölümünde
            örneklem gerekçesi eksik. Aşağıdaki bağlantı kanıta götürür.
          </p>
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            className="w-fit text-[13px] font-medium no-underline"
            style={{ color: accent }}
          >
            Kanıtı görüntüle →
          </a>
          <div
            className="mt-1 rounded-md px-3 py-2 text-[12px]"
            style={{ border: `1px solid ${accent}33`, background: `${accent}14` }}
          >
            <span style={{ color: accent, fontWeight: 600 }}>İpucu:</span> bu
            önizleme yalnızca seçili renk ve yazı tiplerini gösterir.
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusBanner({
  tone,
  icon,
  title,
  body,
}: {
  tone: "ok" | "danger";
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  const color = tone === "ok" ? "var(--color-ok)" : "var(--color-danger)";
  const pale = tone === "ok" ? "var(--color-ok-pale)" : "var(--color-danger-pale)";
  return (
    <div
      role={tone === "ok" ? "status" : "alert"}
      className="flex items-start gap-2.5 rounded-md border px-4 py-3"
      style={{ borderColor: color, background: pale }}
    >
      <span style={{ color }} className="mt-0.5 flex-shrink-0">
        {icon}
      </span>
      <div className="flex flex-col gap-0.5">
        <p className="text-[14px] font-medium" style={{ color }}>
          {title}
        </p>
        <p className="text-[13px] text-ink-mute">{body}</p>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,360px)]"
    >
      <div className="flex flex-col gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-14 animate-pulse rounded-md bg-bg-hover"
          />
        ))}
      </div>
      <div className="h-56 animate-pulse rounded-lg bg-bg-hover" />
      <span className="sr-only">Tema yükleniyor…</span>
    </div>
  );
}

function ErrorBox({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-2 rounded-md border px-4 py-4"
      style={{
        borderColor: "var(--color-danger)",
        background: "var(--color-danger-pale)",
      }}
    >
      <p className="text-[14px] font-medium" style={{ color: "var(--color-danger)" }}>
        Tema yüklenemedi
      </p>
      <p className="text-[13px] text-ink-mute">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-1 rounded-sm border px-3 py-1 text-[13px] font-medium"
        style={{ borderColor: "var(--color-danger)", color: "var(--color-danger)" }}
      >
        Tekrar dene
      </button>
    </div>
  );
}
