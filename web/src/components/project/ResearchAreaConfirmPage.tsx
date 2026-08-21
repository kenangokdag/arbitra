"use client";

// F10-Phase1.5-F7: discovery-1 "Arastirma Alani" onay iskelet.
// Spec: Page_Design/Sayfa_Plani_v1/D_atolye_discovery/discovery-1.md
// Senaryo: kullanici Q (vitrin/OpenAlex) sayfasinda makale gezdi → "Projeye
// Donustur" ile geldi. Sistem Q sorgu/secim baglamindan parsed_understanding
// (3 odak + alan + alt-alan + guven) cikardi ve 3 capa adayi sundu. Kullanici:
// (a) "Onayla → Konu Belirleme" devam eder, (b) "Degistir (Kutuphaneci'yle sohbet)"
// gercek 2-tur sohbet akisina iner (P097 frontend, henuz iskelet — bu sayfa).
//
// F11 Phase A: header artik gercek backend'den (GET /api/project/{id}) seed_query
// + seed_paper_count cekiyor — Q'dan miras snapshot ekrana basildi. Asagidaki
// PARSED + ANCHORS hala fixture (Phase B'de cluster_expander + anchor_finder
// real backend baglanir).

import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowRight, MessageSquarePlus, CheckCircle2, BookOpen, Anchor, ExternalLink } from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";

// F11 Phase A + V1-S16-P001 — GET /api/project/{id} response (api/models/project.py ProjectRead).
// Sadece bu sayfanin gosterdigi alanlar; eski alanlar (anchor, inherited_*) burada
// kullanilmiyor, JSON'da gelse de Pydantic taraf bos donduruyor.
type ParsedUnderstandingApi = {
  focuses: string[];
  field: string;
  subfield: string | null;
  interdisc: boolean;
  confidence: "high" | "med" | "low";
  adviser_text: string;
  finished: boolean;
};

type ProjectReadApi = {
  id: string;
  name: string;
  status: string;
  current_stage: string;
  seed_query: string | null;
  seed_lang: "tr" | "en" | "id" | "other" | null;
  seed_source: "q" | "onboarding" | "manual";
  seed_paper_count: number;
  parsed_understanding: ParsedUnderstandingApi | null;
};

// V1-S14 P004 — POST /api/project/{id}/research-area/anchor-candidates
// (api/models/research_area.py AnchorCandidatesResponse)
type AnchorCandidateApi = {
  paper_id: string;
  title: string;
  abstract_preview: string;
  field: string | null;
  language: string | null;
  year: number | null;
  decision_band: "high" | "med" | "low";
  q_weak: number;
};

type AnchorCandidatesResponseApi = {
  candidates: AnchorCandidateApi[];
  packet_p: string;
  packet_s: string[];
};

// V1-S15.pre A3 — POST /api/project/{id}/research-area/anchor/lock
type LockResponseApi = {
  anchor_paper_id: string;
  locked_at: string;
  cluster_status: "pending" | "expanding" | "ready" | "failed";
};

// V1-S16-P002: PARSED hardcoded fixture KALDIRILDI. parsed_understanding artık
// GET /api/project/{id} response'undan (son adviser turn project_chat_messages)
// geliyor. Null durumda "Sohbete dön" hint gösterilir.

interface AnchorCandidate {
  paperId: string;
  title: string;
  abstractPreview: string;
  field: string;
  language: string;
  year: number;
  decisionBand: "high" | "med" | "low";
  qWeak: number;
}

function mapAnchor(c: AnchorCandidateApi): AnchorCandidate {
  return {
    paperId: c.paper_id,
    title: c.title,
    abstractPreview: c.abstract_preview,
    field: c.field ?? "—",
    language: (c.language ?? "—").toUpperCase(),
    year: c.year ?? 0,
    decisionBand: c.decision_band,
    qWeak: c.q_weak,
  };
}

const CONFIDENCE_TONE: Record<"high" | "med" | "low", { label: string; fg: string; bg: string }> = {
  high: { label: "Yuksek guven", fg: "#0E4F4A", bg: "rgba(14,79,74,0.10)" },
  med: { label: "Orta guven", fg: "#B45309", bg: "rgba(180,83,9,0.10)" },
  low: { label: "Dusuk guven", fg: "#B91C1C", bg: "rgba(185,28,28,0.10)" },
};

const BAND_TONE: Record<"high" | "med" | "low", string> = {
  high: "#0E4F4A",
  med: "#B45309",
  low: "#94a3b8",
};

// ── Component ────────────────────────────────────────────────────────────
export function ResearchAreaConfirmPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "p1";

  // F11 Phase A: gercek backend'den seed_query + seed_paper_count cek.
  // 'p1' demo path'inde (gercek proje yok) 404 doner; sayfa yine acilir,
  // sadece "Source" satirinda "Q sorgusu yuklenemedi" gosterilir.
  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => apiFetch<ProjectReadApi>(`/api/project/${projectId}`),
    enabled: projectId !== "p1",
    retry: false,
    staleTime: 60_000,
  });

  // V1-S14 P004 — POST /api/project/{id}/research-area/anchor-candidates
  // Stage A (parsed_understanding) tamamlanmadıysa 409 stage_a_incomplete döner;
  // 'p1' demo path'inde 404. Hata olunca skeleton boş state gösterir.
  const anchorsQuery = useQuery({
    queryKey: ["research-area-anchors", projectId],
    queryFn: () =>
      apiFetch<AnchorCandidatesResponseApi>(
        `/api/project/${projectId}/research-area/anchor-candidates`,
        { method: "POST" }
      ),
    enabled: projectId !== "p1",
    retry: false,
    staleTime: 60_000,
  });
  const liveAnchors: AnchorCandidate[] = (anchorsQuery.data?.candidates ?? []).map(mapAnchor);

  // V1-S16-P002: parsed_understanding canlı veri (null ise demo placeholder)
  const parsed = projectQuery.data?.parsed_understanding ?? null;

  // V1-S15.pre A3-P006: anchor lock mutation
  const [lockError, setLockError] = useState<string | null>(null);
  const lockMutation = useMutation<LockResponseApi, Error, string>({
    mutationFn: (paperId: string) =>
      apiFetch<LockResponseApi>(
        `/api/project/${projectId}/research-area/anchor/lock`,
        { method: "POST", body: { paper_id: paperId } },
      ),
    onSuccess: () => {
      setLockError(null);
      router.push(`/project/${projectId}/discovery-2`);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        setLockError(
          "Bu proje keşif aşamasından çıktı — çapayı değiştirmek için projeyi sıfırla.",
        );
      } else {
        setLockError(`Çapa kilitlenemedi: ${err.message}`);
      }
    },
  });

  const goConfirm = () => router.push(`/project/${projectId}/discovery-2`);
  const goRevise = () => {
    // P097 gercek Kutuphaneci sohbet akisi henuz baglanmadi — demo'da
    // kullaniciyi ayni sayfada tutuyoruz; gercek implementasyonda chat
    // moduluna gecer (research_area.py POST .../messages).
    alert("Kutuphaneci sohbeti Phase 2'de baglanir (P097 frontend)");
  };

  const tone = CONFIDENCE_TONE[parsed?.confidence ?? "med"];

  return (
    <div data-zone="discovery" className="space-y-6">
      <header className="space-y-2">
        <div
          className="font-mono uppercase"
          style={{
            fontSize: 10,
            letterSpacing: "0.12em",
            color: "var(--color-ink-faint, #64748b)",
          }}
        >
          Kesif · 1.1 · Arastirma Alani
        </div>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1
              className="font-display italic"
              style={{ fontSize: 28, color: "var(--color-ink)", lineHeight: 1.2 }}
            >
              Seni boyle anladim — onayla ya da degistir
            </h1>
            <p style={{ fontSize: 14.5, color: "var(--color-ink-mute)", lineHeight: 1.5 }}>
              Q'da gezdigin makalelerden alanin DNA'sini cikardim. Devam edersen capa kilitlenir,
              sonraki tum modullerin (konu, bibliyometrik, kavram agi, savunma) bu alanla calisir.
            </p>
          </div>
          <span
            className="font-mono whitespace-nowrap"
            style={{
              fontSize: 11,
              letterSpacing: "0.06em",
              color: "var(--color-accent)",
              background: "var(--color-accent-pale)",
              border: "1px solid var(--color-rule)",
              padding: "5px 10px",
              borderRadius: 999,
            }}
          >
            Adim 1.1
          </span>
        </div>
      </header>

      <AdvisorBanner
        zone="discovery"
        message={
          parsed?.adviser_text ??
          "Henüz analiz yok — Kütüphaneci ile sohbeti tamamladıktan sonra bu sayfaya dön."
        }
      />

      {/* F11 Phase A: Q'dan miras snapshot — kullaniciya hangi sorgu+secim
          ile geldigini gosterir. seed_source='q' degilse banner gosterilmez. */}
      {projectQuery.data?.seed_source === "q" && projectQuery.data.seed_query ? (
        <div
          data-testid="q-seed-banner"
          className="flex flex-col gap-1 rounded-lg px-4 py-3"
          style={{
            background: "var(--color-bg-soft)",
            border: "1px solid var(--color-rule)",
          }}
        >
          <div
            className="font-mono uppercase"
            style={{
              fontSize: 9.5,
              letterSpacing: "0.1em",
              color: "var(--color-ink-faint)",
            }}
          >
            Q'dan miras
          </div>
          <div
            className="font-display"
            style={{ fontSize: 13.5, color: "var(--color-ink)" }}
          >
            "{projectQuery.data.seed_query}"
            <span
              className="ml-2 font-mono"
              style={{ fontSize: 11.5, color: "var(--color-ink-faint)" }}
            >
              · {projectQuery.data.seed_paper_count} secim
              {projectQuery.data.seed_lang
                ? ` · ${projectQuery.data.seed_lang.toUpperCase()}`
                : ""}
            </span>
          </div>
        </div>
      ) : null}

      <DemoHint />

      {/* Block 1 — Parsed Understanding kart */}
      <section
        aria-label="Anladigim alan"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2
            className="font-display"
            style={{ fontSize: 17, color: "var(--color-ink)", lineHeight: 1.2 }}
          >
            Anladigim arastirma alani
          </h2>
          <span
            className="font-mono whitespace-nowrap rounded-full px-2.5 py-1"
            style={{
              fontSize: 10.5,
              letterSpacing: "0.05em",
              color: tone.fg,
              background: tone.bg,
              border: `1px solid ${tone.fg}33`,
            }}
          >
            {tone.label}
          </span>
        </div>

        {parsed ? (
          <div className="space-y-4">
            <Field label={`Odaklar (${parsed.focuses.length})`}>
              <div className="flex flex-wrap gap-2">
                {parsed.focuses.map((f, i) => (
                  <span
                    key={i}
                    className="rounded-full px-3 py-1"
                    style={{
                      background: "var(--color-accent-pale)",
                      border: "1px solid var(--color-rule)",
                      color: "var(--color-ink)",
                      fontSize: 12.5,
                    }}
                  >
                    #{f}
                  </span>
                ))}
              </div>
            </Field>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="Alan">
                <div style={{ fontSize: 13.5, color: "var(--color-ink)" }}>{parsed.field}</div>
              </Field>
              <Field label="Alt-alan">
                <div style={{ fontSize: 13.5, color: "var(--color-ink)" }}>
                  {parsed.subfield ?? "—"}
                </div>
              </Field>
              <Field label="Disiplinerlik">
                <div style={{ fontSize: 13.5, color: "var(--color-ink)" }}>
                  {parsed.interdisc ? "Disiplinler-arasi" : "Tek disiplin"}
                </div>
              </Field>
              <Field label="Kaynak">
                <div
                  className="font-mono"
                  style={{ fontSize: 12.5, color: "var(--color-ink-mute)" }}
                >
                  {projectQuery.data?.seed_query
                    ? `Q sorgu: "${projectQuery.data.seed_query}" + ${projectQuery.data.seed_paper_count} secim`
                    : projectQuery.isLoading
                      ? "Q sorgusu yukleniyor…"
                      : "Demo: Q sorgusu yok"}
                </div>
              </Field>
            </div>
          </div>
        ) : (
          <div
            data-testid="parsed-understanding-empty"
            style={{ fontSize: 13, color: "var(--color-ink-mute)", lineHeight: 1.5 }}
          >
            {projectQuery.isLoading
              ? "Analiz yükleniyor…"
              : "Henüz Kütüphaneci sohbeti tamamlanmamış. Yukarıdaki “Değiştir (Kütüphaneci'yle sohbet)” butonu ile sohbete dön; 2-tur tamamlandığında bu alan otomatik dolar."}
          </div>
        )}
      </section>

      {/* Block 2 — Capa adaylari (3 kart) */}
      <section aria-label="Capa adaylari" className="space-y-3">
        <div className="flex items-end justify-between gap-3">
          <h2
            className="font-display"
            style={{ fontSize: 17, color: "var(--color-ink)", lineHeight: 1.2 }}
          >
            Capa adaylari ({liveAnchors.length})
          </h2>
          <p style={{ fontSize: 12, color: "var(--color-ink-faint)" }}>
            HyDE → Pinecone+tsvector → BGE-rerank → top-3
          </p>
        </div>
        {anchorsQuery.isLoading && (
          <p style={{ fontSize: 12, color: "var(--color-ink-faint)" }}>
            Çapa adayları aranıyor…
          </p>
        )}
        {anchorsQuery.isError && (
          <p style={{ fontSize: 12, color: "var(--color-ink-faint)" }}>
            Çapa adayları henüz hazır değil — Kütüphaneci ile sohbeti tamamla
            (Stage A) ardından bu sayfaya dön.
          </p>
        )}
        {!anchorsQuery.isLoading && !anchorsQuery.isError && liveAnchors.length === 0 && (
          <p style={{ fontSize: 12, color: "var(--color-ink-faint)" }}>
            Henüz çapa adayı yok.
          </p>
        )}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {liveAnchors.map((a, idx) => (
            <article
              key={a.paperId}
              className="rounded-xl p-4"
              style={{
                background: "var(--color-bg-card)",
                border: "1px solid var(--color-rule)",
              }}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span
                  className="font-mono"
                  style={{
                    fontSize: 10,
                    letterSpacing: "0.08em",
                    color: "var(--color-ink-faint)",
                  }}
                >
                  Aday {String(idx + 1).padStart(2, "0")}
                </span>
                <span
                  className="font-mono rounded px-1.5 py-0.5"
                  style={{
                    fontSize: 9.5,
                    letterSpacing: "0.06em",
                    color: BAND_TONE[a.decisionBand],
                    background: `${BAND_TONE[a.decisionBand]}14`,
                    border: `1px solid ${BAND_TONE[a.decisionBand]}33`,
                  }}
                >
                  band: {a.decisionBand}
                </span>
              </div>
              <h3
                className="font-display"
                style={{
                  fontSize: 14.5,
                  color: "var(--color-ink)",
                  lineHeight: 1.3,
                  marginBottom: 8,
                }}
              >
                {a.title}
              </h3>
              <p
                className="line-clamp-3"
                style={{
                  fontSize: 12.5,
                  color: "var(--color-ink-mute)",
                  lineHeight: 1.5,
                  marginBottom: 10,
                }}
              >
                {a.abstractPreview}
              </p>
              <div
                className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono"
                style={{ fontSize: 10.5, color: "var(--color-ink-faint)" }}
              >
                <span>{a.year}</span>
                <span>· {a.language}</span>
                <span>· {a.field}</span>
                <span>· q_weak {a.qWeak.toFixed(2)}</span>
              </div>
              <button
                type="button"
                onClick={() => lockMutation.mutate(a.paperId)}
                disabled={lockMutation.isPending}
                data-testid={`lock-anchor-btn-${a.paperId}`}
                className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-white transition hover:brightness-110 disabled:opacity-60"
                style={{ background: "var(--color-accent)", fontSize: 12.5 }}
              >
                <Anchor className="h-3.5 w-3.5" />
                {lockMutation.isPending && lockMutation.variables === a.paperId
                  ? "Kilitleniyor…"
                  : "ÇAPA SEÇ"}
              </button>
              {/* V1-S17 P009 RC5 — paper kartında Detay Link */}
              <Link
                href={`/paper/${a.paperId}`}
                data-testid={`anchor-detay-link-${a.paperId}`}
                className="mt-2 inline-flex w-full items-center justify-center gap-1.5 rounded-lg border px-3 py-1.5 transition hover:bg-stone-50"
                style={{
                  fontSize: 11.5,
                  borderColor: "var(--color-rule)",
                  color: "var(--color-ink-mute)",
                }}
              >
                <ExternalLink className="h-3 w-3" />
                Detay
              </Link>
            </article>
          ))}
        </div>
        {lockError ? (
          <div
            data-testid="lock-error-banner"
            className="rounded-md px-3 py-2"
            style={{
              background: "rgba(185,28,28,0.06)",
              border: "1px solid rgba(185,28,28,0.30)",
              color: "#B91C1C",
              fontSize: 12.5,
            }}
          >
            {lockError}
          </div>
        ) : null}
      </section>

      {/* CTA bar */}
      <div
        className="sticky bottom-4 flex items-center justify-between gap-4 rounded-xl p-4"
        style={{
          background: "var(--color-accent-pale)",
          border: "1px solid var(--color-accent)",
          boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
        }}
      >
        <div className="min-w-0">
          <div
            className="font-display"
            style={{ fontSize: 14.5, color: "var(--color-ink)", lineHeight: 1.3 }}
          >
            Bu alani onayliyor musun?
          </div>
          <p style={{ fontSize: 12.5, color: "var(--color-ink-mute)", marginTop: 2 }}>
            Onayla → Konu Belirleme'de bizim havuzdan top-5 makale dizilir.
          </p>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={goRevise}
            className="inline-flex items-center gap-2 rounded-lg px-4 py-2 transition-colors"
            style={{
              border: "1px solid var(--color-rule)",
              background: "var(--color-bg-card)",
              color: "var(--color-ink-soft)",
              fontSize: 13,
            }}
          >
            <MessageSquarePlus className="h-4 w-4" />
            Degistir (Kutuphaneci'yle sohbet)
          </button>
          <button
            type="button"
            onClick={goConfirm}
            data-testid="confirm-research-area-btn"
            className="inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-white transition hover:brightness-110"
            style={{ background: "var(--color-accent)", fontSize: 13.5 }}
          >
            <CheckCircle2 className="h-4 w-4" />
            Onayla — Konu Belirleme
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div
        className="font-mono uppercase"
        style={{
          fontSize: 9.5,
          letterSpacing: "0.1em",
          color: "var(--color-ink-faint)",
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}

function DemoHint() {
  return (
    <div
      className="flex items-center gap-2 rounded-md px-3 py-2"
      style={{
        background: "var(--color-bg-soft)",
        border: "1px dashed var(--color-rule)",
        fontSize: 12,
        color: "var(--color-ink-faint)",
        fontFamily: "var(--font-mono, ui-monospace)",
        letterSpacing: "0.02em",
      }}
    >
      <BookOpen className="h-3.5 w-3.5" />
      Çapa adaylari canli backend (anchor_finder); Kütüphaneci sohbeti (Stage A) P097 frontend'inde baglanir.
    </div>
  );
}
