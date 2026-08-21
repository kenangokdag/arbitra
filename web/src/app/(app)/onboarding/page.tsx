"use client";

/**
 * /onboarding — F5-S2 PROMPT #4 §1.C frontend reset.
 *
 * Backend sözleşmesi (api/models/onboarding.py):
 *   full_name (2-120) · tier (3-enum) · field_ids[1-3] · subfields[0-3] composite
 *   research_focus (2-500, REQUIRED) · affiliation? · orcid_raw? (regex)
 *
 * K-017: primary_language KALDIRILDI — UI dili browser/locale, DB'de tutulmaz.
 * K-015: research_focus → translator hook backend'de graceful (timeout/fail
 * 502 değil 200 + fallback flag). UI tarafında ek bir gösterge gerekmez.
 *
 * Dim taxonomy (PR #7 merge edildi, 2026-05-04):
 *   GET /api/dim/fields                      — alan listesi (auth-gated, K-025)
 *   GET /api/dim/subfields?field_ids=...     — cascade subfield lazy fetch
 *   @/lib/i18n/fields_tr · subfields_tr      — TR display map (K-012)
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api";
import { fieldDisplay } from "@/lib/i18n/fields_tr";
import { subfieldDisplay } from "@/lib/i18n/subfields_tr";
import type {
  DimField,
  DimFieldListResponse,
  DimSubfield,
  DimSubfieldListResponse,
  OnboardingRequest,
  OnboardingResponse,
  SubfieldRef,
  UserTier,
} from "@/lib/types";

const TIERS: { value: UserTier; label: string; desc: string }[] = [
  { value: "ogrenci", label: "Öğrenci", desc: "Lisans / yüksek lisans / doktora öğrencisi" },
  { value: "arastirmaci", label: "Araştırmacı", desc: "Akademik araştırmacı veya post-doc" },
  { value: "profesyonel", label: "Profesyonel", desc: "Sektörde araştırma yapan uzman" },
];

const MAX_FIELDS = 3;
const MAX_SUBFIELDS = 3;
const RESEARCH_FOCUS_MAX = 500;
const ORCID_PATTERN = /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/;

function tr(field: DimField): string {
  return fieldDisplay(field.field_id, field.name_en);
}

function trSub(sub: DimSubfield): string {
  return subfieldDisplay(sub.subfield_id, sub.name_en);
}

type FieldErrors = {
  banner?: string;
  field_ids?: string;
  subfields?: string;
  research_focus?: string;
  orcid_raw?: string;
};

function mapApiErrorToFields(err: unknown): FieldErrors {
  if (!(err instanceof ApiError)) {
    return { banner: "Bir hata oluştu. Tekrar deneyin." };
  }
  const detail = err.detail as { detail?: unknown } | undefined;
  const inner = detail?.detail ?? detail;

  // 422 — onboarding.py custom HTTPException detail.error
  if (err.status === 422 && inner && typeof inner === "object" && "error" in inner) {
    const code = (inner as { error: string }).error;
    if (code === "invalid_field_ids") {
      const missing = (inner as { missing?: string[] }).missing ?? [];
      return { field_ids: `Geçersiz alan${missing.length ? ": " + missing.join(", ") : ""}.` };
    }
    if (code === "invalid_subfield_pairs") {
      return { subfields: "Seçilen alt-alan parent alanla eşleşmiyor (DB'de bulunamadı)." };
    }
    if (code === "orphan_subfield_ids") {
      return { subfields: "Alt-alan, seçtiğiniz alanlardan birine ait olmalı." };
    }
  }

  // 422 — Pydantic ValidationError (FastAPI detail = list of {loc, msg, type})
  if (err.status === 422 && Array.isArray(inner)) {
    const out: FieldErrors = {};
    for (const item of inner as Array<{ loc?: unknown[]; msg?: string }>) {
      const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
      const msg = item.msg ?? "geçersiz değer";
      if (loc.includes("research_focus")) out.research_focus = msg;
      else if (loc.includes("field_ids")) out.field_ids = msg;
      else if (loc.includes("subfields")) out.subfields = msg;
      else if (loc.includes("orcid_raw")) out.orcid_raw = msg;
      else out.banner = msg;
    }
    return out;
  }

  return { banner: err.message };
}

export default function OnboardingPage() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [tier, setTier] = useState<UserTier>("arastirmaci");
  const [affiliation, setAffiliation] = useState("");
  const [fieldIds, setFieldIds] = useState<string[]>([]);
  const [subfieldKeys, setSubfieldKeys] = useState<Set<string>>(new Set());
  const [researchFocus, setResearchFocus] = useState("");
  const [orcidRaw, setOrcidRaw] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});

  const fieldsQuery = useQuery({
    queryKey: ["dim_fields"],
    queryFn: () => apiFetch<DimFieldListResponse>("/api/dim/fields"),
    staleTime: 5 * 60 * 1000,
  });

  const fieldIdsKey = fieldIds.slice().sort().join(",");
  const subfieldsQuery = useQuery({
    queryKey: ["dim_subfields", fieldIdsKey],
    enabled: fieldIds.length > 0,
    queryFn: () => {
      const qs = new URLSearchParams();
      for (const fid of fieldIds) qs.append("field_ids", fid);
      return apiFetch<DimSubfieldListResponse>(`/api/dim/subfields?${qs.toString()}`);
    },
    staleTime: 5 * 60 * 1000,
  });

  const fields = fieldsQuery.data?.fields ?? [];
  const subfieldOptions = subfieldsQuery.data?.subfields ?? [];

  // Field değişince geçersiz hale gelen alt-alanları temizle.
  function toggleField(fid: string) {
    setErrors({});
    setFieldIds((prev) => {
      if (prev.includes(fid)) {
        const next = prev.filter((x) => x !== fid);
        // Bu field'a ait subfield seçimleri de temizlensin.
        setSubfieldKeys((sk) => {
          const out = new Set(sk);
          for (const k of sk) {
            const [, parentFid] = k.split("|");
            if (parentFid === fid) out.delete(k);
          }
          return out;
        });
        return next;
      }
      if (prev.length >= MAX_FIELDS) return prev; // max-3 sessiz reddet (UI disable + tooltip)
      return [...prev, fid];
    });
  }

  function toggleSubfield(sub: DimSubfield) {
    setErrors({});
    const key = `${sub.subfield_id}|${sub.field_id}`;
    setSubfieldKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else if (next.size < MAX_SUBFIELDS) {
        next.add(key);
      }
      return next;
    });
  }

  const subfieldsPayload = useMemo<SubfieldRef[]>(
    () =>
      Array.from(subfieldKeys).map((k) => {
        const parts = k.split("|");
        return { subfield_id: parts[0] ?? "", field_id: parts[1] ?? "" };
      }),
    [subfieldKeys],
  );

  const mutation = useMutation({
    mutationFn: () => {
      const payload: OnboardingRequest = {
        full_name: fullName.trim(),
        tier,
        field_ids: fieldIds,
        subfields: subfieldsPayload,
        research_focus: researchFocus.trim(),
        ...(affiliation.trim() ? { affiliation: affiliation.trim() } : {}),
        ...(orcidRaw.trim() ? { orcid_raw: orcidRaw.trim() } : {}),
      };
      return apiFetch<OnboardingResponse>("/api/onboarding", {
        method: "POST",
        body: payload,
      });
    },
    onSuccess: () => {
      setErrors({});
      router.push("/");
    },
    onError: (err) => setErrors(mapApiErrorToFields(err)),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next: FieldErrors = {};
    if (fullName.trim().length < 2) next.banner = "Ad Soyad en az 2 karakter olmalı.";
    if (fieldIds.length < 1) next.field_ids = "En az 1 alan seçin.";
    if (researchFocus.trim().length < 2) {
      next.research_focus = "Araştırma odağı zorunlu (en az 2 karakter).";
    }
    if (researchFocus.trim().length > RESEARCH_FOCUS_MAX) {
      next.research_focus = `En fazla ${RESEARCH_FOCUS_MAX} karakter.`;
    }
    if (orcidRaw.trim() && !ORCID_PATTERN.test(orcidRaw.trim())) {
      next.orcid_raw = "ORCID formatı: 0000-0000-0000-0000 (son hane X olabilir).";
    }
    if (Object.keys(next).length > 0) {
      setErrors(next);
      return;
    }
    setErrors({});
    mutation.mutate();
  }

  const fieldsAtMax = fieldIds.length >= MAX_FIELDS;
  const subsAtMax = subfieldKeys.size >= MAX_SUBFIELDS;
  const focusLen = researchFocus.trim().length;

  return (
    <>
      <PageHeader
        title="Hoş Geldin"
        lede="Arbitra'yı sizin için en iyi şekilde ayarlayalım. Bu bilgileri sonra Profilim'den de değiştirebilirsiniz."
      />

      <Card className="mx-auto max-w-2xl">
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          {/* ── Bölüm 1: Kimlik ── */}
          <div className="flex flex-col gap-4">
            <h3 className="text-[13px] font-medium uppercase tracking-wider text-ink-mute">
              Kimlik
            </h3>

            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-ink-soft">
                Ad Soyad
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Prof. Dr. Ahmet Yılmaz"
                required
                minLength={2}
                maxLength={120}
                className="w-full rounded-sm border border-rule bg-bg px-3.5 py-2 text-[14px] text-ink outline-none placeholder:text-ink-mute focus:border-accent focus:ring-2 focus:ring-accent/25"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-ink-soft">
                Profiliniz
              </label>
              <div className="flex flex-col gap-2">
                {TIERS.map((t) => (
                  <label
                    key={t.value}
                    className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors duration-150 ${
                      tier === t.value
                        ? "border-accent bg-accent/5"
                        : "border-rule hover:bg-bg-hover"
                    }`}
                  >
                    <input
                      type="radio"
                      name="tier"
                      value={t.value}
                      checked={tier === t.value}
                      onChange={() => setTier(t.value)}
                      className="mt-0.5"
                    />
                    <div>
                      <div className="text-[14px] font-medium text-ink">{t.label}</div>
                      <div className="text-[12.5px] text-ink-mute">{t.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-ink-soft">
                Kurum <span className="text-ink-faint">(opsiyonel)</span>
              </label>
              <input
                type="text"
                value={affiliation}
                onChange={(e) => setAffiliation(e.target.value)}
                placeholder="Örn: İstanbul Üniversitesi"
                maxLength={200}
                className="w-full rounded-sm border border-rule bg-bg px-3.5 py-2 text-[14px] text-ink outline-none placeholder:text-ink-mute focus:border-accent focus:ring-2 focus:ring-accent/25"
              />
            </div>
          </div>

          {/* ── Bölüm 2: Araştırma alanı ── */}
          <div className="flex flex-col gap-4 border-t border-rule pt-5">
            <h3 className="text-[13px] font-medium uppercase tracking-wider text-ink-mute">
              Araştırma Alanı
            </h3>

            <div>
              <div className="mb-1.5 flex items-baseline justify-between">
                <label className="block text-[13px] font-medium text-ink-soft">
                  Birincil alan(lar) <span className="text-ink-faint">— en az 1, en çok {MAX_FIELDS}</span>
                </label>
                <span className="text-[12px] text-ink-faint">
                  {fieldIds.length}/{MAX_FIELDS}
                </span>
              </div>
              {fieldsQuery.isLoading ? (
                <div className="text-[13px] text-ink-mute">Alanlar yükleniyor…</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {fields.map((f) => {
                    const selected = fieldIds.includes(f.field_id);
                    const disabled = !selected && fieldsAtMax;
                    return (
                      <button
                        key={f.field_id}
                        type="button"
                        onClick={() => toggleField(f.field_id)}
                        disabled={disabled}
                        title={disabled ? `En çok ${MAX_FIELDS} alan seçilebilir` : tr(f)}
                        className={`rounded-full border px-3 py-1.5 text-[13px] transition-colors duration-150 ${
                          selected
                            ? "border-accent bg-accent/10 text-ink"
                            : "border-rule bg-bg-card text-ink-soft hover:bg-bg-hover"
                        } disabled:cursor-not-allowed disabled:opacity-40`}
                      >
                        {tr(f)}
                      </button>
                    );
                  })}
                </div>
              )}
              {errors.field_ids ? (
                <div className="mt-2 text-[13px] text-red-700">{errors.field_ids}</div>
              ) : null}
            </div>

            {fieldIds.length > 0 ? (
              <div>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <label className="block text-[13px] font-medium text-ink-soft">
                    Alt-alan(lar) <span className="text-ink-faint">— opsiyonel, en çok {MAX_SUBFIELDS}</span>
                  </label>
                  <span className="text-[12px] text-ink-faint">
                    {subfieldKeys.size}/{MAX_SUBFIELDS}
                  </span>
                </div>
                {subfieldsQuery.isLoading ? (
                  <div className="text-[13px] text-ink-mute">Alt-alanlar yükleniyor…</div>
                ) : subfieldOptions.length === 0 ? (
                  <div className="text-[13px] text-ink-mute">
                    Seçtiğiniz alanlar için alt-alan tanımlı değil.
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {subfieldOptions.map((s) => {
                      const key = `${s.subfield_id}|${s.field_id}`;
                      const selected = subfieldKeys.has(key);
                      const disabled = !selected && subsAtMax;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => toggleSubfield(s)}
                          disabled={disabled}
                          title={disabled ? `En çok ${MAX_SUBFIELDS} alt-alan seçilebilir` : trSub(s)}
                          className={`rounded-full border px-3 py-1.5 text-[12.5px] transition-colors duration-150 ${
                            selected
                              ? "border-accent bg-accent/10 text-ink"
                              : "border-rule bg-bg-card text-ink-soft hover:bg-bg-hover"
                          } disabled:cursor-not-allowed disabled:opacity-40`}
                        >
                          {trSub(s)}
                        </button>
                      );
                    })}
                  </div>
                )}
                {errors.subfields ? (
                  <div className="mt-2 text-[13px] text-red-700">{errors.subfields}</div>
                ) : null}
              </div>
            ) : null}
          </div>

          {/* ── Bölüm 3: Araştırma odağı + ORCID ── */}
          <div className="flex flex-col gap-4 border-t border-rule pt-5">
            <h3 className="text-[13px] font-medium uppercase tracking-wider text-ink-mute">
              Odak
            </h3>

            <div>
              <div className="mb-1.5 flex items-baseline justify-between">
                <label className="block text-[13px] font-medium text-ink-soft">
                  Araştırma odağınız <span className="text-red-700">*</span>
                </label>
                <span className="text-[12px] text-ink-faint">
                  {focusLen}/{RESEARCH_FOCUS_MAX}
                </span>
              </div>
              <textarea
                value={researchFocus}
                onChange={(e) => setResearchFocus(e.target.value)}
                placeholder="Örn: çok kriterli karar verme yöntemleriyle hastane personeli performans değerlendirmesi"
                required
                minLength={2}
                maxLength={RESEARCH_FOCUS_MAX}
                rows={3}
                className="w-full resize-none rounded-sm border border-rule bg-bg px-3.5 py-2 text-[14px] text-ink outline-none placeholder:text-ink-mute focus:border-accent focus:ring-2 focus:ring-accent/25"
              />
              <div className="mt-1 text-[12px] text-ink-faint">
                Türkçe yazabilirsiniz — sistem dahili kullanım için akademik İngilizce&apos;ye çevirir
                (kişisel bilgileriniz değişmez).
              </div>
              {errors.research_focus ? (
                <div className="mt-2 text-[13px] text-red-700">{errors.research_focus}</div>
              ) : null}
            </div>

            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-ink-soft">
                ORCID <span className="text-ink-faint">(opsiyonel)</span>
              </label>
              <input
                type="text"
                value={orcidRaw}
                onChange={(e) => setOrcidRaw(e.target.value)}
                placeholder="0000-0000-0000-0000"
                pattern="\d{4}-\d{4}-\d{4}-\d{3}[\dX]"
                className="w-full rounded-sm border border-rule bg-bg px-3.5 py-2 text-[14px] text-ink outline-none placeholder:text-ink-mute focus:border-accent focus:ring-2 focus:ring-accent/25"
              />
              {/* KVKK: ORCID raw asla saklanmaz; backend SHA-256 hash'ler. */}
              <div className="mt-1 text-[12px] text-ink-faint">
                ORCID raw saklanmaz; sadece hash&apos;lenmiş hâli kullanılır (KVKK).
              </div>
              {errors.orcid_raw ? (
                <div className="mt-2 text-[13px] text-red-700">{errors.orcid_raw}</div>
              ) : null}
            </div>
          </div>

          {errors.banner ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-3.5 py-2.5 text-[13px] text-red-700">
              {errors.banner}
            </div>
          ) : null}

          <Button
            type="submit"
            size="lg"
            disabled={
              mutation.isPending ||
              fullName.trim().length < 2 ||
              fieldIds.length < 1 ||
              researchFocus.trim().length < 2
            }
            className="w-full"
          >
            {mutation.isPending ? "Kaydediliyor…" : "Başlayalım"}
          </Button>
        </form>
      </Card>
    </>
  );
}
