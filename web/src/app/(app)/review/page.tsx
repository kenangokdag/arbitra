// F14 Hakemlik — yükleme sayfası.
// Sade upload (drag-drop / dosya seç) + mod (yazar/editör) + dil → POST /api/review/upload.
// Başarınca /review/{job_id}'ye yönlendir.

"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  Info,
  Loader2,
  Lock,
  ShieldAlert,
  ShieldCheck,
  UploadCloud,
  X,
} from "lucide-react";

import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";
import { ReviewOnboardingTour } from "@/components/review/ReviewOnboardingTour";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { BRAND_TAGLINE_TR } from "@/lib/brand";
import {
  fetchMyReviewJobs,
  uploadReview,
  type ConfidentialityMode,
  type ExternalAIConsent,
  type ReviewLang,
  type ReviewMode,
  type UserJob,
} from "@/lib/review-api";
import {
  hasSeenReviewTour,
  markReviewTourSeen,
} from "@/lib/reviewTourPreference";

const ACCEPT = ".doc,.docx,.pdf,.tex,.zip";
const ACCEPT_HINT = "Word, PDF, LaTeX veya ZIP";

const MODE_OPTIONS: { value: ReviewMode; label: string; hint: string }[] = [
  {
    value: "author",
    label: "Yazar",
    hint: "Göndermeden önce kendi makaleni değerlendir",
  },
  {
    value: "editor",
    label: "Editör",
    hint: "Dergi tarafı: gelen makaleyi hakem gözüyle incele",
  },
];

const LANG_OPTIONS: { value: ReviewLang; label: string }[] = [
  { value: "tr", label: "Türkçe" },
  { value: "en", label: "İngilizce" },
];

// --- gizlilik / rıza seçenekleri (SEC-2; backend api/routes/review.py:155-158) ---

const AUTHOR_OPTIONS: { value: boolean; label: string; hint: string }[] = [
  {
    value: true,
    label: "Kendi makalem",
    hint: "Yazarı benim; gönderim öncesi öz-değerlendirme",
  },
  {
    value: false,
    label: "Başkasının makalesi",
    hint: "Hakem/editör olarak başkasına ait gizli bir makaleyi inceliyorum",
  },
];

const CONFIDENTIALITY_OPTIONS: {
  value: ConfidentialityMode;
  label: string;
  hint: string;
}[] = [
  {
    value: "author_owned",
    label: "Yazar-sahipli",
    hint: "Makale bana ait; paylaşımını ben kontrol ediyorum",
  },
  {
    value: "reviewer_confidential",
    label: "Gizli hakemlik",
    hint: "Yayımlanmamış, başkasına ait gizli makale",
  },
];

const CONSENT_OPTIONS: {
  value: ExternalAIConsent;
  label: string;
  hint: string;
}[] = [
  {
    value: "allowed",
    label: "İzin ver",
    hint: "Tam hakem-paneli için harici yapay zekâ kullanılabilir",
  },
  {
    value: "blocked",
    label: "Engelle",
    hint: "Harici yapay zekâ kullanılmaz; yalnız deterministik analiz",
  },
  {
    value: "requires_private_mode",
    label: "Yalnız yerel model",
    hint: "Harici sağlayıcı yok; yerel-model gerekir (bugün deterministik-only sayılır)",
  },
];

const RETENTION_MIN = 1;
const RETENTION_MAX = 365;

// Sürtünme düşürme (2C): 8 düz alan → 3 mantıksal adım. Numaralı eyebrow,
// kullanıcıya "neredeyim / kaç adım kaldı" hissini verir (gizli karmaşa →
// aşamalı). Gizlilik ayrı bir adım = gömülü ince yazı değil, görünür güven-anı.
function StepHeading({
  step,
  title,
  hint,
}: {
  step: number;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono-pmid text-[11px] uppercase tracking-[0.12em] text-ink-faint">
        Adım {step} / 3
      </span>
      <h2 className="serif text-[19px] font-medium italic text-ink">{title}</h2>
      {hint ? (
        <p className="max-w-[68ch] text-[12.5px] leading-relaxed text-ink-mute">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export default function ReviewUploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<ReviewMode>("author");
  const [language, setLanguage] = useState<ReviewLang>("tr");
  // Gizlilik / rıza — backend default'larıyla aynı başlangıç (yazar akışı).
  const [isAuthor, setIsAuthor] = useState(true);
  const [confidentialityMode, setConfidentialityMode] =
    useState<ConfidentialityMode>("author_owned");
  const [externalAiConsent, setExternalAiConsent] =
    useState<ExternalAIConsent>("allowed");
  const [retentionDays, setRetentionDays] = useState(30);
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // REVIEW_ONBOARDING_TURU_2026-08-17 — SADECE ilk girişte. useEffect'te
  // kontrol edilir (client-only, SSR/hydration uyuşmazlığı olmasın diye
  // başlangıç state'i her zaman false, mount sonrası güncellenir).
  const [showTour, setShowTour] = useState(false);
  useEffect(() => {
    if (!hasSeenReviewTour()) setShowTour(true);
  }, []);
  function closeTour() {
    markReviewTourSeen();
    setShowTour(false);
  }

  // VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §3.3 — kullanıcının BİLİNÇLİ seçtiği
  // önceki versiyon (otomatik/sessiz eşleştirme YOK). Hiç geçmiş job yoksa
  // (ilk yükleme deneyimi) bölüm HİÇ gösterilmez.
  const [myJobs, setMyJobs] = useState<UserJob[]>([]);
  const [parentJobId, setParentJobId] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    fetchMyReviewJobs()
      .then((res) => {
        if (!cancelled) setMyJobs(res.jobs);
      })
      .catch(() => {
        // sessiz atlanır — seçici sadece bir kolaylık, upload akışını bloklamaz
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // consent_gate.resolve_privacy'nin güvenli default'unu UI'da AYNALA:
  // gizli makalede consent yalnız AÇIKÇA 'allowed' ise izinli; aksi blocked.
  // Bu yüzden gizliliğe geçince consent'i güvenli tarafa (blocked) çekeriz,
  // yazar-sahipliye dönünce default 'allowed'. Kullanıcı sonra elle değiştirebilir.
  function applyConfidentiality(c: ConfidentialityMode) {
    setConfidentialityMode(c);
    setExternalAiConsent(c === "reviewer_confidential" ? "blocked" : "allowed");
  }

  function chooseIsAuthor(v: boolean) {
    setIsAuthor(v);
    applyConfidentiality(v ? "author_owned" : "reviewer_confidential");
  }

  // external_ai_allowed (consent_gate): yalnız 'allowed' → harici YZ çalışır.
  const isConfidential = confidentialityMode === "reviewer_confidential";
  const externalAiWillRun = externalAiConsent === "allowed";
  const deterministicOnly = !externalAiWillRun;

  function pickFile(f: File | undefined | null) {
    if (!f) return;
    setError(null);
    setFile(f);
  }

  async function start() {
    if (!file || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await uploadReview({
        file,
        mode,
        language,
        isAuthor,
        confidentialityMode,
        externalAiConsent,
        retentionDays,
        parentJobId: parentJobId || undefined,
      });
      router.push(`/review/${res.job_id}`);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Yükleme başarısız (${err.status})`
          : err instanceof Error
            ? err.message
            : "Yükleme başarısız oldu";
      setError(msg);
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {showTour ? <ReviewOnboardingTour onClose={closeTour} /> : null}

      {/* ARBITRA marka başlığı — wordmark + tagline + kısa işlevsel açıklama */}
      <header className="mb-[22px] flex flex-col gap-3">
        <div className="flex items-baseline gap-3">
          <ArbitraWordmark size="xl" />
          <span className="font-mono-pmid text-[11px] uppercase tracking-[0.12em] text-ink-faint">
            Hakemlik
          </span>
        </div>
        <p className="text-[14px] font-medium text-ink-soft">{BRAND_TAGLINE_TR}</p>
        <p className="max-w-[720px] text-[14px] leading-relaxed text-ink-mute">
          Word/PDF/LaTeX/ZIP yükleyin; atıf-doğrulamalı Stanford-kalite hakem
          raporu alın. Atıf bütünlüğü, kapsam ve istatistik kontrolleri
          deterministik motorla; yorum ve karar çok-personalı değerlendirmeyle
          üretilir.
        </p>
      </header>

      {/* Yükleme kutusu */}
      <section className="flex flex-col gap-4">
        <StepHeading
          step={1}
          title="Makaleni yükle"
          hint="Word, PDF, LaTeX veya ZIP. Tek dosya yeterli; gerisini motor halleder."
        />
        <div
          role="button"
          tabIndex={0}
          aria-label={`Dosya seç veya sürükle (${ACCEPT_HINT})`}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pickFile(e.dataTransfer.files?.[0]);
          }}
          className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-md border border-dashed bg-bg-card px-6 py-12 text-center transition-colors duration-150 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-accent"
          style={{
            borderColor: dragging ? "var(--color-accent)" : "var(--color-rule)",
            background: dragging ? "var(--color-accent-pale)" : undefined,
          }}
        >
          <UploadCloud
            className="h-8 w-8 text-ink-faint"
            strokeWidth={1.75}
            aria-hidden
          />
          <div>
            <p className="text-[15px] font-medium text-ink">
              Dosyayı buraya sürükle ya da seç
            </p>
            <p className="mt-1 text-[13px] text-ink-mute">{ACCEPT_HINT}</p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
        </div>

        {/* Seçili dosya */}
        {file ? (
          <div className="flex items-center justify-between gap-3 rounded-md border border-rule bg-bg-card px-4 py-3 shadow-sm">
            <span className="flex min-w-0 items-center gap-2.5">
              <FileText
                className="h-4 w-4 flex-shrink-0 text-accent"
                aria-hidden
              />
              <span className="min-w-0 truncate text-[14px] text-ink">
                {file.name}
              </span>
              <span className="flex-shrink-0 font-mono-pmid text-[11px] text-ink-faint">
                {(file.size / 1024).toFixed(0)} KB
              </span>
            </span>
            <button
              type="button"
              onClick={() => setFile(null)}
              aria-label="Dosyayı kaldır"
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-sm text-ink-faint transition-colors hover:bg-bg-hover hover:text-ink"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : null}

        {/* Önceki versiyon seçici — SADECE geçmiş job varsa görünür, varsayılan
            seçim YOK (kullanıcı BİLİNÇLİ seçer, otomatik/sessiz bağlama YOK). */}
        {myJobs.length > 0 ? (
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="parent-job-select"
              className="text-[12.5px] text-ink-mute"
            >
              Bu makalenin önceki bir versiyonu var mı? (opsiyonel)
            </label>
            <select
              id="parent-job-select"
              value={parentJobId}
              onChange={(e) => setParentJobId(e.target.value)}
              className="rounded-md border border-rule bg-bg-card px-3 py-2 text-[13.5px] text-ink"
            >
              <option value="">Hayır, yeni makale</option>
              {myJobs.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.source_name ?? "(isimsiz)"} —{" "}
                  {new Date(j.created_at).toLocaleDateString("tr-TR")}
                </option>
              ))}
            </select>
          </div>
        ) : null}
      </section>

      {/* Adım 2 — Değerlendirme türü + dil (tek mantıksal grup) */}
      <StepHeading
        step={2}
        title="Değerlendirme türü ve dil"
        hint="Kendi makaleni mi gönderiyorsun, yoksa hakem/editör olarak mı bakıyorsun? Raporu hangi dilde istiyorsun?"
      />

      {/* Mod seçimi */}
      <section className="flex flex-col gap-2.5">
        <span className="text-[13px] font-semibold uppercase tracking-wider text-ink-mute">
          Değerlendirme modu
        </span>
        <div className="grid gap-3 sm:grid-cols-2">
          {MODE_OPTIONS.map((opt) => {
            const active = mode === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setMode(opt.value)}
                aria-pressed={active}
                className="rounded-md border bg-bg-card px-4 py-3 text-left transition-colors duration-150"
                style={{
                  borderColor: active
                    ? "var(--color-accent)"
                    : "var(--color-rule)",
                  background: active ? "var(--color-accent-pale)" : undefined,
                }}
              >
                <div
                  className="text-[14px] font-medium"
                  style={{
                    color: active ? "var(--color-accent)" : "var(--color-ink)",
                  }}
                >
                  {opt.label}
                </div>
                <div className="mt-0.5 text-[12.5px] text-ink-mute">
                  {opt.hint}
                </div>
              </button>
            );
          })}
        </div>

        {/* Editör modu seçilince gizlilik sorumluluğu notu (R-4) */}
        {mode === "editor" ? (
          <div
            className="flex items-start gap-2.5 rounded-md border-l-2 px-3.5 py-2.5"
            style={{
              borderColor: "var(--color-warn)",
              background: "var(--color-warn-pale)",
            }}
            role="note"
          >
            <ShieldAlert
              className="mt-0.5 h-4 w-4 flex-shrink-0"
              style={{ color: "var(--color-warn)" }}
              aria-hidden
            />
            <p className="text-[12.5px] leading-relaxed text-ink-soft">
              Editör modu: yayımlanmamış makalenin gizliliği sizin
              sorumluluğunuzdadır. Bu değerlendirme yol göstericidir, insan
              hakemin yerine geçmez; derginizin LLM-hakemlik politikasını
              kontrol edin.
            </p>
          </div>
        ) : null}
      </section>

      {/* Dil seçimi */}
      <section className="flex flex-col gap-2.5">
        <span className="text-[13px] font-semibold uppercase tracking-wider text-ink-mute">
          Rapor dili
        </span>
        <div className="flex gap-2">
          {LANG_OPTIONS.map((opt) => {
            const active = language === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setLanguage(opt.value)}
                aria-pressed={active}
                className="rounded-sm border px-4 py-2 text-[13px] font-medium transition-colors duration-150"
                style={{
                  borderColor: active
                    ? "var(--color-accent)"
                    : "var(--color-rule)",
                  background: active
                    ? "var(--color-accent-pale)"
                    : "var(--color-bg-card)",
                  color: active ? "var(--color-accent)" : "var(--color-ink-soft)",
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </section>

      {/* Adım 3 — Gizlilik & rıza (SEC-2; görünür güven-anı, gömülü ince yazı
          DEĞİL). backend Form: is_author / confidentiality_mode /
          external_ai_consent / retention_days (api/routes/review.py:155-158) */}
      <StepHeading
        step={3}
        title="Gizlilik ve güven"
        hint="Makaleni nasıl koruyacağımıza sen karar verirsin: harici yapay zekâ kullanılsın mı, dosya ne kadar süre tutulsun? Aşağıdaki seçimler raporun davranışını gerçekten değiştirir."
      />
      <section
        className="flex flex-col gap-4 rounded-md border border-rule-soft bg-bg-card px-5 py-5"
      >
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="h-4 w-4 flex-shrink-0 text-accent" aria-hidden />
          <span className="text-[13px] font-semibold uppercase tracking-wider text-ink-mute">
            Gizlilik ve yapay zekâ rızası
          </span>
        </div>

        {/* Yazarlık: kendi makalem mi, başkasının gizli makalesi mi */}
        <div className="flex flex-col gap-2">
          <span className="text-[12.5px] font-medium text-ink-soft">
            Bu makalenin yazarı kim?
          </span>
          <div className="grid gap-3 sm:grid-cols-2">
            {AUTHOR_OPTIONS.map((opt) => {
              const active = isAuthor === opt.value;
              return (
                <button
                  key={String(opt.value)}
                  type="button"
                  onClick={() => chooseIsAuthor(opt.value)}
                  aria-pressed={active}
                  className="rounded-md border bg-bg-card px-4 py-3 text-left transition-colors duration-150"
                  style={{
                    borderColor: active
                      ? "var(--color-accent)"
                      : "var(--color-rule)",
                    background: active ? "var(--color-accent-pale)" : undefined,
                  }}
                >
                  <div
                    className="text-[14px] font-medium"
                    style={{
                      color: active
                        ? "var(--color-accent)"
                        : "var(--color-ink)",
                    }}
                  >
                    {opt.label}
                  </div>
                  <div className="mt-0.5 text-[12.5px] text-ink-mute">
                    {opt.hint}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Gizlilik modu */}
        <div className="flex flex-col gap-2">
          <span className="text-[12.5px] font-medium text-ink-soft">
            Gizlilik durumu
          </span>
          <div className="grid gap-3 sm:grid-cols-2">
            {CONFIDENTIALITY_OPTIONS.map((opt) => {
              const active = confidentialityMode === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => applyConfidentiality(opt.value)}
                  aria-pressed={active}
                  className="rounded-md border bg-bg-card px-4 py-3 text-left transition-colors duration-150"
                  style={{
                    borderColor: active
                      ? "var(--color-accent)"
                      : "var(--color-rule)",
                    background: active ? "var(--color-accent-pale)" : undefined,
                  }}
                >
                  <div
                    className="text-[14px] font-medium"
                    style={{
                      color: active
                        ? "var(--color-accent)"
                        : "var(--color-ink)",
                    }}
                  >
                    {opt.label}
                  </div>
                  <div className="mt-0.5 text-[12.5px] text-ink-mute">
                    {opt.hint}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Harici yapay zekâ rızası */}
        <div className="flex flex-col gap-2">
          <span className="text-[12.5px] font-medium text-ink-soft">
            Harici yapay zekâ kullanımı
          </span>
          <div className="grid gap-2 sm:grid-cols-3">
            {CONSENT_OPTIONS.map((opt) => {
              const active = externalAiConsent === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setExternalAiConsent(opt.value)}
                  aria-pressed={active}
                  className="rounded-md border bg-bg-card px-4 py-3 text-left transition-colors duration-150"
                  style={{
                    borderColor: active
                      ? "var(--color-accent)"
                      : "var(--color-rule)",
                    background: active ? "var(--color-accent-pale)" : undefined,
                  }}
                >
                  <div
                    className="text-[13.5px] font-medium"
                    style={{
                      color: active
                        ? "var(--color-accent)"
                        : "var(--color-ink)",
                    }}
                  >
                    {opt.label}
                  </div>
                  <div className="mt-0.5 text-[12px] leading-snug text-ink-mute">
                    {opt.hint}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Canlı sonuç açıklaması — consent_gate gerçek davranışını yansıtır.
            Her kontrol değişince bu metin değişir (ölü kontrol yok). */}
        {deterministicOnly ? (
          <div
            className="flex items-start gap-2.5 rounded-md border-l-2 px-3.5 py-2.5"
            style={{
              borderColor: "var(--color-warn)",
              background: "var(--color-warn-pale)",
            }}
            role="status"
          >
            <Lock
              className="mt-0.5 h-4 w-4 flex-shrink-0"
              style={{ color: "var(--color-warn)" }}
              aria-hidden
            />
            <p className="text-[12.5px] leading-relaxed text-ink-soft">
              {isConfidential ? (
                <>
                  <strong>Gizli makale:</strong> harici yapay zekâ varsayılan
                  olarak <strong>ENGELLİDİR</strong>.{" "}
                </>
              ) : null}
              Harici yapay zekâ <strong>kullanılmayacak</strong>. Rapor yalnız
              deterministik analizdir (atıf bütünlüğü, istatistik ve kapsam
              kontrolleri); hakem-paneli (LLM) yargısı çalıştırılmaz. Tam
              inceleme için yukarıdan “İzin ver”i seçin.
            </p>
          </div>
        ) : isConfidential ? (
          <div
            className="flex items-start gap-2.5 rounded-md border-l-2 px-3.5 py-2.5"
            style={{
              borderColor: "var(--color-warn)",
              background: "var(--color-warn-pale)",
            }}
            role="status"
          >
            <ShieldAlert
              className="mt-0.5 h-4 w-4 flex-shrink-0"
              style={{ color: "var(--color-warn)" }}
              aria-hidden
            />
            <p className="text-[12.5px] leading-relaxed text-ink-soft">
              Açık rıza verdiniz: bu <strong>gizli</strong> makale tam
              hakem-paneli için harici yapay zekâ sağlayıcılara gönderilecek.
              Derginizin LLM-hakemlik politikasını kontrol edin.
            </p>
          </div>
        ) : (
          <div
            className="flex items-start gap-2.5 rounded-md border-l-2 px-3.5 py-2.5"
            style={{
              borderColor: "var(--color-accent)",
              background: "var(--color-accent-pale)",
            }}
            role="status"
          >
            <ShieldCheck
              className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent"
              aria-hidden
            />
            <p className="text-[12.5px] leading-relaxed text-ink-soft">
              Tam hakem-paneli çalışacak; atıf/istatistik/kapsam kontrollerine ek
              olarak çok-personalı değerlendirme için harici yapay zekâ
              kullanılabilir.
            </p>
          </div>
        )}

        {/* Saklama süresi */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="retention-days"
            className="text-[12.5px] font-medium text-ink-soft"
          >
            Saklama süresi (gün)
          </label>
          <div className="flex items-center gap-2.5">
            <input
              id="retention-days"
              type="number"
              min={RETENTION_MIN}
              max={RETENTION_MAX}
              value={retentionDays}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (Number.isNaN(n)) return;
                setRetentionDays(
                  Math.min(RETENTION_MAX, Math.max(RETENTION_MIN, Math.trunc(n))),
                );
              }}
              className="w-28 rounded-sm border border-rule bg-bg-card px-3 py-2 text-[13px] text-ink focus:border-accent focus:outline-none"
            />
            <span className="flex items-center gap-1.5 text-[12px] text-ink-faint">
              <Info className="h-3.5 w-3.5" aria-hidden />
              {RETENTION_MIN}–{RETENTION_MAX} gün; bu süre sonunda yüklenen dosya
              silinir.
            </span>
          </div>
        </div>
      </section>

      {error ? (
        <p
          role="alert"
          className="rounded-md border px-4 py-3 text-[13px]"
          style={{
            borderColor: "var(--color-danger)",
            background: "var(--color-danger-pale)",
            color: "var(--color-danger)",
          }}
        >
          {error}
        </p>
      ) : null}

      {/* Başlat */}
      <div className="flex items-center gap-3">
        <Button
          variant="ritual"
          size="lg"
          onClick={start}
          disabled={!file || submitting}
          isLoading={submitting}
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Yükleniyor…
            </>
          ) : (
            "İncelemeyi başlat"
          )}
        </Button>
        {!file ? (
          <span className="text-[12.5px] text-ink-faint">
            Önce bir dosya seç
          </span>
        ) : null}
      </div>
    </div>
  );
}
