// F14 Hakemlik — VERDICT KOKPİTİ (DESIGN-DECISIONS §5: 3 katmanlı aşamalı açığa
// çıkarma). v2 raporda 18-bölüm düz scroll DEĞİL; editöryal omurga:
//   KATMAN 1 — Verdict (karar + tek-cümle teşhis + hazırlık skoru + ölümcül risk)
//   KATMAN 2 — Risk → kanıt → düzeltme drill'i (İMZA ANI: makaledeki cümleye
//              çıpa + neden + fix yan yana)
//   KATMAN 3 — Uzman katmanı (hakem heyeti, kanıt paketi, künye) — collapse.
// v1 rapor (v2 alanları yok) ESKİSİ GİBİ render edilir (isV2 guard; geri-uyum).

"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Download,
  FileText,
  Gavel,
  HelpCircle,
  Info,
  Layers,
  Loader2,
  MessageCircle,
  MinusCircle,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  Wrench,
  X,
  XCircle,
} from "lucide-react";

import {
  ActionItemCard,
  PRIORITY_LABEL,
  PRIORITY_TOKEN,
} from "@/components/review/ActionItemCard";
import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";
import { ConfidenceMeter } from "@/components/review/ConfidenceMeter";
import { DegradedNotice } from "@/components/review/DegradedNotice";
import { EvidenceBadge } from "@/components/review/EvidenceBadge";
import { ManuscriptAnchorLink } from "@/components/review/ManuscriptAnchorLink";
import { RiskBadge } from "@/components/review/RiskBadge";
import { BRAND } from "@/lib/brand";
import {
  DIMENSION_LABELS,
  VERDICT_LABELS,
  fetchReviewReportDocx,
  type ActionItem,
  type ActionPriority,
  type AIUsageDisclosure,
  type CitationStatus,
  type ContextSupport,
  type CouncilRole,
  type DimensionKey,
  type DimensionScore,
  type DocumentClassification,
  type DocumentType,
  type EvidencePack,
  type ExecutiveVerdict,
  type Finding,
  type ManuscriptAnchor,
  type ParsedReference,
  type ReviewerCouncilItem,
  type ReviewReport,
  type RiskRadarItem,
  type SectionReview,
  type StudyDesign,
  type Verdict,
  type VersionComparison,
} from "@/lib/review-api";
import { useOpenChatbox } from "@/stores/ui";

// verdict → renk eşlemesi (statü token'ları, dekoratif değil semantik)
const VERDICT_TOKEN: Record<Verdict, { color: string; pale: string }> = {
  accept: { color: "var(--color-ok)", pale: "var(--color-ok-pale)" },
  minor_revision: { color: "var(--color-info)", pale: "var(--color-info-pale)" },
  major_revision: { color: "var(--color-warn)", pale: "var(--color-warn-pale)" },
  reject: { color: "var(--color-danger)", pale: "var(--color-danger-pale)" },
};

export function ReviewReportView({
  report,
  jobId,
  comparison,
}: {
  report: ReviewReport;
  jobId: string;
  // VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §3.5 — üstte ([jobId]/page.tsx)
  // çekilip PROP olarak geçilir; component kendi içinde useQuery ÇAĞIRMAZ
  // (mevcut testler QueryClientProvider'sız render ediyor). Opsiyonel —
  // undefined/null ise hiçbir şey render edilmez, mevcut davranış korunur.
  comparison?: VersionComparison | null;
}) {
  // Açık çıpa drawer'ı (bulgu → makaledeki yer + alıntı). Tek-tık erişim.
  const [openAnchor, setOpenAnchor] = useState<ManuscriptAnchor | null>(null);

  // v2 mı? schema_version v2 VEYA herhangi bir v2 alanı dolu. Soyulmuş v1
  // raporda (alanlar undefined) bu false → v1 render birebir korunur.
  const isV2 =
    report.schema_version?.startsWith("review_report.v2") === true ||
    report.executive_verdict != null ||
    report.disclosure != null ||
    report.document_classification != null ||
    (report.risk_radar?.length ?? 0) > 0 ||
    (report.reviewer_council?.length ?? 0) > 0 ||
    (report.findings?.length ?? 0) > 0 ||
    (report.action_plan?.length ?? 0) > 0 ||
    (report.section_reviews?.length ?? 0) > 0;

  return (
    <article className="flex flex-col gap-8">
      {/* İnce ARBITRA künyesi — kokpit'in üstünde sakin imza şeridi. */}
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden
          className="h-3 w-[2px] flex-shrink-0 rounded-full"
          style={{ background: "var(--color-accent)" }}
        />
        <ArbitraWordmark size="sm" />
        <span className="font-mono-pmid text-[10.5px] uppercase tracking-[0.12em] text-ink-faint">
          Hakem raporu
        </span>
        <span className="flex-1" />
        <AskAdvisorButton jobId={jobId} />
        <DownloadDocxButton jobId={jobId} />
      </div>

      <VersionComparisonSummary comparison={comparison ?? null} />

      {isV2 ? (
        <VerdictCockpit
          report={report}
          jobId={jobId}
          onOpenAnchor={setOpenAnchor}
        />
      ) : (
        <V1Report report={report} jobId={jobId} />
      )}

      {/* Çıpa drawer'ı — bulgudan makaledeki yere tek tık (İMZA ANI yüzeyi). */}
      <AnchorDrawer anchor={openAnchor} onClose={() => setOpenAnchor(null)} />
    </article>
  );
}

// --- Danışman tetikleyicisi (DANISMAN_FRONTEND_KABLOLAMA_2026-08-19) -------
// mode="review_advisor" + reportId=jobId ile ChatboxPanel'i açar. pageState
// BİLİNÇLİ OLARAK gönderilmiyor — rapor verisi zaten backend'de report_id
// üzerinden sahip-kapsamlı çekiliyor (review_service.get_report), pageState
// (istemciden gelen, sahtelenebilir) burada gereksiz/çakışan bir kanal olurdu.

function AskAdvisorButton({ jobId }: { jobId: string }) {
  const openChatbox = useOpenChatbox();

  return (
    <button
      type="button"
      onClick={() =>
        openChatbox({ kind: "advisor", mode: "review_advisor", reportId: jobId })
      }
      data-testid="ask-advisor-button"
      aria-label="Bu rapor hakkında Danışman'a sor"
      className="flex items-center gap-1.5 rounded-md border border-rule-soft bg-bg-card px-2.5 py-1 text-[11.5px] font-medium text-ink-mute transition-colors hover:border-accent hover:text-ink"
    >
      <MessageCircle className="h-3.5 w-3.5" aria-hidden />
      <span>Danışman&apos;a sor</span>
    </button>
  );
}

// --- rapor indirme (RAPOR_DOCX_EXPORT_2026-08-16 §3.2) ---------------------
// Standart tarayıcı "diske indir" idiomu: blob → createObjectURL → geçici
// <a download> → click → revokeObjectURL. AudioPlayButton.tsx'teki blob'u
// INLINE çalan desenden FARKLI — burada gerçekten diske indiriyoruz.

function DownloadDocxButton({ jobId }: { jobId: string }) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setError(null);
    setIsLoading(true);
    try {
      const blob = await fetchReviewReportDocx(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `arbitra-rapor-${jobId}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "İndirilemedi.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoading}
        data-testid="download-docx-button"
        aria-label="Raporu Word olarak indir"
        className="flex items-center gap-1.5 rounded-md border border-rule-soft bg-bg-card px-2.5 py-1 text-[11.5px] font-medium text-ink-mute transition-colors hover:border-accent hover:text-ink disabled:cursor-wait disabled:opacity-60"
      >
        {isLoading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
        ) : (
          <Download className="h-3.5 w-3.5" aria-hidden />
        )}
        <span>{isLoading ? "Hazırlanıyor…" : "İndir (.docx)"}</span>
      </button>
      {error ? (
        <span data-testid="download-docx-error" className="text-[11px] text-rose-600">
          {error}
        </span>
      ) : null}
    </div>
  );
}

// --- versiyon karşılaştırma özeti (VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17) --
// Katman 1'in üstünde, comparison PROP olarak verilirse (üstte [jobId]/page.tsx
// çeker) render edilir. SADECE deterministik özet — bulgu-eşleştirme YOK
// (Faz 2, ayrı oturum, plan §5: Finding.finding_id iki koşum arasında stabil
// değil, bulanık eşleştirme guardian gerektiren ayrı bir karar).

function DeltaText({ value, parens = false }: { value: number | null; parens?: boolean }) {
  if (value === null) {
    return <span className="text-ink-faint">bilinmiyor</span>;
  }
  const rounded = Math.round(value * 10) / 10;
  if (rounded === 0) {
    return <span className="text-ink-faint">değişmedi</span>;
  }
  const positive = rounded > 0;
  const text = `${positive ? "+" : ""}${rounded}`;
  return (
    <span
      className="font-mono-pmid tabular-nums"
      style={{ color: positive ? "var(--color-ok)" : "var(--color-danger)" }}
    >
      {parens ? `(${text})` : text}
    </span>
  );
}

function VersionComparisonSummary({
  comparison,
}: {
  comparison: VersionComparison | null;
}) {
  if (!comparison) return null;

  const hasReadiness =
    comparison.previous_readiness_score !== null ||
    comparison.current_readiness_score !== null;

  return (
    <section
      data-testid="version-comparison-summary"
      className="flex flex-col gap-3 rounded-md border border-rule-soft bg-bg-card px-4 py-3.5"
    >
      <span className="font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-ink-faint">
        Önceki versiyona göre
      </span>

      <div className="flex flex-wrap items-center gap-2 text-[13.5px]">
        {comparison.verdict_changed ? (
          <>
            <span className="text-ink-mute">
              {VERDICT_LABELS[comparison.previous_verdict]}
            </span>
            <ArrowRight className="h-3.5 w-3.5 text-ink-faint" aria-hidden />
            <span className="font-medium text-ink">
              {VERDICT_LABELS[comparison.current_verdict]}
            </span>
          </>
        ) : (
          <span className="text-ink-soft">
            Karar aynı:{" "}
            <span className="font-medium">
              {VERDICT_LABELS[comparison.current_verdict]}
            </span>
          </span>
        )}
      </div>

      {hasReadiness ? (
        <div className="flex flex-wrap items-center gap-2 text-[13px]">
          <span className="text-ink-mute">Hazırlık puanı:</span>
          {comparison.previous_readiness_score !== null ? (
            <span className="font-mono-pmid text-ink-faint">
              {Math.round(comparison.previous_readiness_score)}
            </span>
          ) : null}
          {comparison.previous_readiness_score !== null &&
          comparison.current_readiness_score !== null ? (
            <ArrowRight className="h-3 w-3 text-ink-faint" aria-hidden />
          ) : null}
          {comparison.current_readiness_score !== null ? (
            <span className="font-mono-pmid font-medium text-ink">
              {Math.round(comparison.current_readiness_score)}
            </span>
          ) : null}
          <DeltaText value={comparison.readiness_delta} parens />
        </div>
      ) : null}

      {comparison.dimension_deltas.length > 0 ? (
        <ul
          data-testid="version-comparison-dimension-deltas"
          className="flex flex-col divide-y divide-rule-soft"
        >
          {comparison.dimension_deltas.map((d) => (
            <li
              key={d.key}
              className="flex items-center justify-between gap-3 py-1.5 text-[12.5px]"
            >
              <span className="text-ink-soft">{humanizeDimension(d.key)}</span>
              <DeltaText value={d.delta} />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

// ===========================================================================
// VERDICT KOKPİTİ — 3 katmanlı aşamalı açığa çıkarma (DESIGN-DECISIONS §5)
// ===========================================================================

function VerdictCockpit({
  report,
  jobId,
  onOpenAnchor,
}: {
  report: ReviewReport;
  jobId: string;
  onOpenAnchor: (anchor: ManuscriptAnchor) => void;
}) {
  const ev = report.executive_verdict ?? null;
  const radar = report.risk_radar ?? [];
  const council = report.reviewer_council ?? [];
  const findings = report.findings ?? [];
  const actions = report.action_plan ?? [];
  const sections = report.section_reviews ?? [];
  const ep = report.evidence_pack;

  // bulgu/aksiyon join haritaları (risk→bulgu→fix tek görsel iplik, 2B)
  const findingById = new Map(findings.map((f) => [f.finding_id, f]));
  const actionById = new Map(actions.map((a) => [a.action_id, a]));

  // rıza nedeniyle çekirdek boşsa: beyaz ekran yerine dürüst hal
  const consentDegraded = report.disclosure?.degraded_due_to_consent === true;
  const coreEmpty = !ev && findings.length === 0 && radar.length === 0;

  return (
    <div className="flex flex-col gap-10">
      {/* ===== KATMAN 1 — VERDICT (ilk açılış, en iri, üstte) ===== */}
      <section data-testid="cockpit-layer-1" className="flex flex-col gap-6">
        {consentDegraded && coreEmpty ? (
          <DegradedNotice
            reason={
              report.disclosure?.note ??
              "Harici yapay zekâ onayı verilmediği için tam değerlendirme üretilemedi. Aşağıdaki şeffaflık bölümünde ayrıntı yer alıyor."
            }
          />
        ) : null}

        <ExecutiveVerdictHero
          verdict={ev}
          fallbackVerdict={report.verdict}
          title={report.manuscript_meta.title ?? "Başlıksız makale"}
          classification={report.document_classification ?? null}
          consentDegraded={consentDegraded}
          dimensionScores={report.dimension_scores}
        />

        <EthicsNotice report={report} />
        <EditorDigest report={report} />

        {ev ? <TopFatalRisks risks={ev.top_fatal_risks} /> : null}
      </section>

      {/* ===== ÖNCELİKLİ DÜZELTMELER — Katman 1 ile 2 arası, HER ZAMAN açık
          (RAPOR_ONCELIKLI_DUZELTME_LISTESI_2026-08-16, Kenan kararı) ===== */}
      <PrioritizedActionSection actions={actions} findingById={findingById} />

      {/* ===== KATMAN 2 — RİSK → KANIT → DÜZELTME (talep-üzerine drill) ===== */}
      <section data-testid="cockpit-layer-2" className="flex flex-col gap-4">
        <LayerHeading
          eyebrow="Katman 2 · Kanıt"
          title="Riskten kanıta, kanıttan düzeltmeye"
          hint="Bir riske dokunun: bağlı bulgular, makalenizdeki tam cümle (çıpa) ve önerilen düzeltme yan yana açılır."
        />
        <RiskDrillSection
          radar={radar}
          findings={findings}
          actionById={actionById}
          onOpenAnchor={onOpenAnchor}
        />
      </section>

      {/* ===== KATMAN 3 — UZMAN KATMANI (en alt, collapse) ===== */}
      <Layer3Expert
        report={report}
        jobId={jobId}
        council={council}
        findingById={findingById}
        ep={ep}
        sections={sections}
      />

      {/* Şeffaflık alt-bilgisi (AI kullanımı) — VARSA her zaman görünür (§7). */}
      {report.disclosure ? (
        <DisclosureFooter disclosure={report.disclosure} />
      ) : null}
    </div>
  );
}

// --- katman başlığı (editöryal omurga: bölüm üst-etiketi) -------------------

function LayerHeading({
  eyebrow,
  title,
  hint,
}: {
  eyebrow: string;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono-pmid text-[10.5px] uppercase tracking-[0.12em] text-ink-faint">
        {eyebrow}
      </span>
      <h2 className="serif text-[22px] font-medium italic text-ink">{title}</h2>
      {hint ? (
        <p className="max-w-[72ch] text-[12.5px] leading-relaxed text-ink-mute">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

// --- KATMAN 1: yönetici özeti (kahraman) -----------------------------------
// Karar EN İRİ; tek-cümle teşhis altında; hazırlık skoru TEŞHİSİN ALTINDA,
// dekoratif bant değil — bağlam içinde (DESIGN-DECISIONS §2).

function ExecutiveVerdictHero({
  verdict,
  fallbackVerdict,
  title,
  classification,
  consentDegraded,
  dimensionScores,
}: {
  verdict: ExecutiveVerdict | null;
  fallbackVerdict: Verdict;
  title: string;
  classification: DocumentClassification | null;
  consentDegraded: boolean;
  dimensionScores: DimensionScore[];
}) {
  // verdict yoksa (rıza-düşürülmüş) bile dürüst bir başlık göster, çökme.
  const decision = verdict?.recommended_decision ?? fallbackVerdict;
  const token = VERDICT_TOKEN[decision];

  return (
    <header
      data-testid="executive-verdict"
      className="flex flex-col gap-5 border-b border-rule pb-7"
    >
      <div className="flex flex-col gap-1.5">
        <span className="font-mono-pmid text-[11px] uppercase tracking-[0.12em] text-ink-faint">
          Hakem kararı
        </span>
        <h1
          data-testid="exec-decision"
          className="serif text-[44px] font-medium leading-[1.02] tracking-[-0.02em]"
          style={{ color: token.color }}
        >
          {VERDICT_LABELS[decision]}
        </h1>
        <p className="max-w-[68ch] text-[13px] leading-relaxed text-ink-mute">
          {title}
        </p>
      </div>

      {verdict ? (
        <>
          {/* tek-cümle teşhis — kararın gerekçesi, iri serif */}
          <p className="serif max-w-[68ch] text-[19px] leading-snug text-ink">
            {verdict.one_sentence_diagnosis}
          </p>

          {/* hazırlık skoru — TEŞHİSİN ALTINDA, bağlamla (dekor değil) */}
          <ReadinessLine
            score={verdict.overall_readiness_score}
            confidence={verdict.confidence}
          />

          {/* "sadece 84/100 gösterip bırakma" — sınırlayıcı boyut vurgusu
              (SINIRLAYICI_BOYUT_VURGUSU_2026-08-16) */}
          <LimitingDimensionCallout dimensionScores={dimensionScores} />
        </>
      ) : (
        <p className="text-[13.5px] leading-relaxed text-ink-mute">
          {consentDegraded
            ? "Onay kısıtı nedeniyle yönetici özeti üretilemedi; karar yalnız deterministik analize dayanır (ayrıntı: şeffaflık bölümü)."
            : "Bu rapor için yönetici özeti üretilmedi."}
        </p>
      )}

      {classification ? (
        <div className="flex flex-wrap items-center gap-2">
          <FileText className="h-3.5 w-3.5 text-ink-faint" aria-hidden />
          <span className="text-[12.5px] text-ink-mute">
            {DOC_TYPE_LABELS[classification.document_type]} ·{" "}
            {STUDY_DESIGN_LABELS[classification.study_design]}
          </span>
          {classification.rationale ? (
            <span className="text-[12px] italic text-ink-faint">
              — {classification.rationale}
            </span>
          ) : null}
        </div>
      ) : null}
    </header>
  );
}

function ReadinessLine({
  score,
  confidence,
}: {
  score: number;
  confidence: number;
}) {
  const readiness = Math.round(Math.min(100, Math.max(0, score)));
  return (
    <div className="flex flex-col gap-2.5 rounded-md border border-rule-soft bg-bg-soft px-4 py-3.5">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono-pmid text-[11px] uppercase tracking-[0.1em] text-ink-faint">
          Hazırlık puanı
        </span>
        <span className="flex items-baseline gap-1">
          <span
            data-testid="exec-readiness"
            className="font-mono-pmid text-[26px] font-medium tabular-nums leading-none text-ink"
          >
            {readiness}
          </span>
          <span className="font-mono-pmid text-[13px] text-ink-faint">/ 100</span>
        </span>
      </div>
      {/* açıklayıcı — "ret @ 89/100" çelişki gibi okunmasın */}
      <p className="max-w-[68ch] text-[12px] leading-relaxed text-ink-mute">
        Karar en ağır bulguların ciddiyetine göre verilir; hazırlık puanı ise
        boyutların ortalamasıdır. Bu yüzden düşük bir karar, görece yüksek bir
        puanla birlikte görülebilir.
      </p>
      <ConfidenceMeter
        value={confidence}
        label="Karar güveni"
        className="max-w-xs"
      />
    </div>
  );
}

// --- KATMAN 1: sınırlayıcı boyut vurgusu ------------------------------------
// SINIRLAYICI_BOYUT_VURGUSU_2026-08-16 — plan §1.2 dürüst sınır:
// overall_readiness_score GERÇEKTE risk_radar'ın ortalamasından hesaplanıyor
// (engine/academic/report_synthesis.py:616-620), dimension_scores'tan DEĞİL.
// "En düşük dimension_score" iyi bir YAKLAŞIK gösterge ama readiness'in
// matematiksel olarak KANITLANMIŞ tek nedeni DEĞİL — bu yüzden metin "değerlendirilen
// 10 boyut arasında" diyor, "asıl sebep bu" gibi aşırı-iddialı dil KULLANMIYOR.

// 7 boyut risk_radar ile deterministik köprülü (report_synthesis.py:704-712,
// _DIMENSION_KEY_TO_RISK) — berabere durumunda bunlar LLM-yalnız 3 boyuttan
// (importance/community_value/contextualization) ÖNCELİKLİDİR (daha temellendirilmiş
// gerekçe: rationale risk_radar'ın why_it_matters'ına dayanıyor).
const _RADAR_LINKED_DIMENSIONS = new Set<DimensionKey>([
  "citation_integrity",
  "statistical_consistency",
  "coverage_completeness",
  "clarity",
  "soundness",
  "claims_supported",
  "originality",
]);

// api/models/review.py:79-92'deki DimensionKey şema sırası — berabere durumunun
// son, stabil/testable adımı.
const DIMENSION_KEY_ORDER: DimensionKey[] = [
  "originality",
  "importance",
  "claims_supported",
  "soundness",
  "clarity",
  "community_value",
  "contextualization",
  "citation_integrity",
  "coverage_completeness",
  "statistical_consistency",
];

function findLimitingDimension(
  scores: DimensionScore[],
): DimensionScore | null {
  if (scores.length === 0) return null;
  const minScore = Math.min(...scores.map((d) => d.score));
  const candidates = scores.filter((d) => d.score === minScore);
  if (candidates.length === 1) return candidates[0]!;

  const grounded = candidates.filter((d) =>
    _RADAR_LINKED_DIMENSIONS.has(d.key),
  );
  const pool = grounded.length > 0 ? grounded : candidates;

  return [...pool].sort(
    (a, b) =>
      DIMENSION_KEY_ORDER.indexOf(a.key) - DIMENSION_KEY_ORDER.indexOf(b.key),
  )[0]!;
}

function LimitingDimensionCallout({
  dimensionScores,
}: {
  dimensionScores: DimensionScore[];
}) {
  const limiting = findLimitingDimension(dimensionScores);
  if (!limiting) return null;

  return (
    <div
      data-testid="limiting-dimension-callout"
      data-dimension={limiting.key}
      className="flex flex-col gap-1.5 rounded-md border-l-2 bg-bg-card px-4 py-3"
      style={{ borderColor: "var(--color-warn)" }}
    >
      <p className="text-[12.5px] leading-relaxed text-ink-soft">
        Değerlendirilen 10 boyut arasında seni en çok{" "}
        <span className="font-medium text-ink">
          {humanizeDimension(limiting.key)}
        </span>{" "}
        geride tutuyor{" "}
        <span className="font-mono-pmid text-ink-faint">
          ({limiting.score.toFixed(1)} / 10)
        </span>
        .
      </p>
      <p className="text-[12.5px] leading-relaxed text-ink-mute">
        {limiting.rationale}
      </p>
    </div>
  );
}

// --- KATMAN 1: en kritik riskler -------------------------------------------

function TopFatalRisks({ risks }: { risks: string[] }) {
  if (risks.length === 0) {
    return (
      <EmptyNote>Bu rapor için kritik risk işaretlenmedi.</EmptyNote>
    );
  }
  return (
    <div className="flex flex-col gap-2.5">
      <h3 className="flex items-center gap-2 font-mono-pmid text-[11px] uppercase tracking-[0.1em] text-ink-faint">
        <AlertOctagon
          className="h-3.5 w-3.5"
          style={{ color: "var(--color-danger)" }}
          aria-hidden
        />
        En kritik riskler
      </h3>
      <ul data-testid="top-fatal-risks" className="flex flex-col gap-2">
        {risks.map((r, i) => (
          <li
            key={i}
            className="flex items-start gap-2.5 rounded-md border-l-2 bg-bg-card px-4 py-2.5"
            style={{ borderColor: "var(--color-danger)" }}
          >
            <AlertOctagon
              className="mt-0.5 h-4 w-4 flex-shrink-0"
              style={{ color: "var(--color-danger)" }}
              aria-hidden
            />
            <span className="text-[13.5px] leading-relaxed text-ink-soft">
              {r}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// --- ÖNCELİKLİ DÜZELTME LİSTESİ ---------------------------------------------
// RAPOR_ONCELIKLI_DUZELTME_LISTESI_2026-08-16 — Katman 1 ile 2 arasında, HER
// ZAMAN açık. Bilinçli tekrar: bir fix hem burada hem Katman 2'nin drill'inde
// (ilgili risk satırı açılınca) görünebilir — bug değil, "her zaman açık +
// üstte" kararının doğal sonucu (plan §2.2).

const PRIORITY_ORDER: ActionPriority[] = ["P0", "P1", "P2"];

function _worstLinkedSeverity(
  action: ActionItem,
  findingById: Map<string, Finding>,
): Finding["severity"] {
  let worst: Finding["severity"] = "info";
  for (const id of action.linked_finding_ids) {
    const f = findingById.get(id);
    if (f && SEVERITY_RANK[f.severity] < SEVERITY_RANK[worst]) {
      worst = f.severity;
    }
  }
  return worst;
}

function PrioritizedActionSection({
  actions,
  findingById,
}: {
  actions: ActionItem[];
  findingById: Map<string, Finding>;
}) {
  const grouped = new Map<ActionPriority, ActionItem[]>();
  for (const a of actions) {
    const arr = grouped.get(a.priority) ?? [];
    arr.push(a);
    grouped.set(a.priority, arr);
  }
  for (const arr of grouped.values()) {
    arr.sort(
      (a, b) =>
        SEVERITY_RANK[_worstLinkedSeverity(a, findingById)] -
        SEVERITY_RANK[_worstLinkedSeverity(b, findingById)],
    );
  }

  return (
    <section data-testid="priority-actions" className="flex flex-col gap-4">
      <LayerHeading
        eyebrow="Önceliklendirilmiş"
        title="Önce ne yapmalısın?"
        hint="Bulgulardan türetilen düzeltmeler, öncelik sırasına göre."
      />
      {actions.length === 0 ? (
        <EmptyNote>
          Bu rapor için önceliklendirilmiş bir düzeltme aksiyonu işaretlenmedi.
        </EmptyNote>
      ) : (
        <div className="flex flex-col gap-6">
          {PRIORITY_ORDER.filter((p) => (grouped.get(p)?.length ?? 0) > 0).map(
            (p) => (
              <div key={p} data-testid="priority-group" data-priority={p} className="flex flex-col gap-2.5">
                <h3
                  className="font-mono-pmid text-[11px] uppercase tracking-[0.08em]"
                  style={{ color: PRIORITY_TOKEN[p] }}
                >
                  {PRIORITY_LABEL[p]}
                </h3>
                <ul className="flex flex-col gap-2.5">
                  {grouped.get(p)!.map((a) => (
                    <li key={a.action_id} className="flex flex-col gap-1.5">
                      <ActionItemCard item={a} />
                      {a.linked_finding_ids.length > 0 ? (
                        <p className="pl-1 text-[12px] text-ink-faint">
                          İlgili bulgu:{" "}
                          {a.linked_finding_ids
                            .map((id) => findingById.get(id)?.title ?? id)
                            .join(" · ")}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ),
          )}
        </div>
      )}
    </section>
  );
}

// --- KATMAN 2: risk → bulgu → fix drill'i ----------------------------------

function RiskDrillSection({
  radar,
  findings,
  actionById,
  onOpenAnchor,
}: {
  radar: RiskRadarItem[];
  findings: Finding[];
  actionById: Map<string, ActionItem>;
  onOpenAnchor: (anchor: ManuscriptAnchor) => void;
}) {
  // boyut → bulgular (risk radar.dimension ile finding.dimension eşleşir)
  const byDimension = new Map<string, Finding[]>();
  for (const f of findings) {
    const arr = byDimension.get(f.dimension) ?? [];
    arr.push(f);
    byDimension.set(f.dimension, arr);
  }

  // ciddiyet-sıralı radar (critical → info; eşitlikte düşük skor önce;
  // score=null [değerlendirilmedi] sona düşer, "kötü" ile karışmasın)
  const sortedRadar = [...radar].sort((a, b) => {
    const severityDiff = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    if (severityDiff !== 0) return severityDiff;
    if (a.score === null && b.score === null) return 0;
    if (a.score === null) return 1;
    if (b.score === null) return -1;
    return a.score - b.score;
  });

  // radar'da temsil edilen boyutlar dışında kalan bulgular kaybolmasın
  const radarDims = new Set(sortedRadar.map((r) => r.dimension));
  const leftover = findings.filter((f) => !radarDims.has(f.dimension));

  if (radar.length === 0 && findings.length === 0) {
    return <EmptyNote>Boyut riski hesaplanmadı, bulgu kaydedilmedi.</EmptyNote>;
  }

  return (
    <div data-testid="risk-radar" className="flex flex-col gap-3">
      <ul className="flex flex-col gap-3">
        {sortedRadar.map((item) => (
          <RiskDrillRow
            key={item.dimension}
            item={item}
            findings={byDimension.get(item.dimension) ?? []}
            actionById={actionById}
            onOpenAnchor={onOpenAnchor}
          />
        ))}
      </ul>

      {leftover.length > 0 ? (
        <div className="flex flex-col gap-2.5">
          <h3 className="font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-ink-faint">
            Diğer bulgular
          </h3>
          <ul data-testid="findings-other" className="flex flex-col gap-2.5">
            {[...leftover]
              .sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])
              .map((f) => (
                <FindingDetail
                  key={f.finding_id}
                  finding={f}
                  actionById={actionById}
                  onOpenAnchor={onOpenAnchor}
                />
              ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function RiskDrillRow({
  item,
  findings,
  actionById,
  onOpenAnchor,
}: {
  item: RiskRadarItem;
  findings: Finding[];
  actionById: Map<string, ActionItem>;
  onOpenAnchor: (anchor: ManuscriptAnchor) => void;
}) {
  const [open, setOpen] = useState(false);
  const score =
    item.score === null ? null : Math.round(Math.min(100, Math.max(0, item.score)));
  const ordered = [...findings].sort(
    (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity],
  );
  const hasDrill = ordered.length > 0;

  return (
    <li
      data-testid="risk-radar-item"
      data-dimension={item.dimension}
      className="overflow-hidden rounded-md border border-rule-soft bg-bg-card"
    >
      <button
        type="button"
        onClick={() => hasDrill && setOpen((v) => !v)}
        aria-expanded={hasDrill ? open : undefined}
        disabled={!hasDrill}
        className="flex w-full flex-col gap-2 px-4 py-3 text-left disabled:cursor-default"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-2 text-[14px] font-medium text-ink">
            {hasDrill ? (
              <ChevronDown
                className="h-4 w-4 flex-shrink-0 text-ink-faint transition-transform duration-150"
                style={{ transform: open ? "rotate(180deg)" : undefined }}
                aria-hidden
              />
            ) : (
              <span aria-hidden className="h-4 w-4 flex-shrink-0" />
            )}
            {humanizeDimension(item.dimension)}
          </span>
          <div className="flex items-center gap-2.5">
            <RiskBadge severity={item.severity} />
            <span className="font-mono-pmid text-[13px] tabular-nums text-ink-soft">
              {score === null ? "Değerlendirilmedi" : `${score} / 100`}
            </span>
          </div>
        </div>
        {item.why_it_matters ? (
          <p className="pl-6 text-[13px] leading-relaxed text-ink-mute">
            {item.why_it_matters}
          </p>
        ) : null}
        <div className="pl-6">
          <ConfidenceMeter
            value={item.confidence}
            label="Güven"
            className="max-w-xs"
          />
        </div>
        {hasDrill ? (
          <span className="pl-6 text-[12px] font-medium text-accent">
            {open
              ? "Bulguları gizle"
              : `${ordered.length} bulgu · kanıt ve düzeltmeyi gör →`}
          </span>
        ) : (
          <span className="pl-6 text-[12px] text-ink-faint">
            Bu boyut için bağlı bulgu yok.
          </span>
        )}
      </button>

      {open && hasDrill ? (
        <ul
          data-testid="findings"
          className="flex flex-col gap-2.5 border-t border-rule-soft bg-bg-soft px-4 py-3.5"
        >
          {ordered.map((f) => (
            <FindingDetail
              key={f.finding_id}
              finding={f}
              actionById={actionById}
              onOpenAnchor={onOpenAnchor}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

// İMZA ANI — bulgu kartı: makaledeki cümle (çıpa) + neden + düzeltme yan yana.
function FindingDetail({
  finding,
  actionById,
  onOpenAnchor,
}: {
  finding: Finding;
  actionById: Map<string, ActionItem>;
  onOpenAnchor: (anchor: ManuscriptAnchor) => void;
}) {
  const fixes = finding.action_item_ids
    .map((id) => actionById.get(id))
    .filter((a): a is ActionItem => a != null);

  return (
    <li
      data-testid="finding-card"
      data-finding-id={finding.finding_id}
      className="flex flex-col gap-2.5 rounded-md border border-rule-soft bg-bg-card px-4 py-3.5"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="text-[14.5px] font-semibold text-ink">{finding.title}</h3>
        <RiskBadge severity={finding.severity} />
      </div>

      {finding.summary ? (
        <p className="max-w-[72ch] text-[13.5px] leading-relaxed text-ink-soft">
          {finding.summary}
        </p>
      ) : null}

      <ConfidenceMeter
        value={finding.confidence}
        label="Bulgu güveni"
        className="max-w-xs"
      />

      {/* NEDEN — kriter gerekçesi */}
      {finding.reasoning_public ? (
        <p className="max-w-[72ch] border-l-2 border-rule-soft pl-3 text-[12.5px] italic leading-relaxed text-ink-mute">
          {finding.reasoning_public}
        </p>
      ) : null}

      {/* ÇIPA — makalendeki tam cümle (tek tıkla drawer). HER ZAMAN görünür,
          3 dürüst durum (FINDING_KAYNAK_ALINTI_TUTARLILIGI_2026-08-16 Katman A):
          anchor var / belge-geneli sorun / konum yapısal olarak belirtilmedi.
          Üçüncü durum, motorun kanıt-zorunluluğunun sadece critical/major
          severity'de garanti olmasının (engine/academic/_engine_base.py:295-310)
          GÖRÜNÜR bir yansıması — veri eksikliğini SAKLAMIYORUZ. */}
      <div className="flex flex-col gap-1.5">
        <span className="font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-ink-faint">
          Makalendeki yer
        </span>
        {finding.manuscript_anchors.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {finding.manuscript_anchors.map((a) => (
              <ManuscriptAnchorLink
                key={a.anchor_id}
                anchor={a}
                onOpen={() => onOpenAnchor(a)}
              />
            ))}
          </div>
        ) : finding.global_issue ? (
          <p
            data-testid="finding-source-global"
            className="text-[12px] italic text-ink-faint"
          >
            Bu belge geneli bir sorun — tek bir cümleye işaret edilmiyor.
          </p>
        ) : (
          <p
            data-testid="finding-source-unspecified"
            className="text-[12px] italic text-ink-faint"
          >
            Kaynak konumu yapısal olarak belirtilmedi.
          </p>
        )}
      </div>

      {/* DÜZELTME — bağlı action_item (risk→bulgu→fix tek iplik, 2B) */}
      {fixes.length > 0 ? (
        <div data-testid="finding-fix" className="flex flex-col gap-2 pt-0.5">
          <span className="flex items-center gap-1.5 font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-accent">
            <Wrench className="h-3 w-3" aria-hidden />
            Bu bulgu için düzeltme
            <ArrowRight className="h-3 w-3" aria-hidden />
          </span>
          {fixes.map((a) => (
            <ActionItemCard key={a.action_id} item={a} />
          ))}
        </div>
      ) : null}

      {finding.limitations.length > 0 ? (
        <ul className="flex flex-col gap-0.5 pt-0.5">
          {finding.limitations.map((l, i) => (
            <li key={i} className="text-[12px] leading-relaxed text-ink-faint">
              · {l}
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

// --- KATMAN 3: uzman katmanı (en alt, collapse) ----------------------------

function Layer3Expert({
  report,
  jobId,
  council,
  findingById,
  ep,
  sections,
}: {
  report: ReviewReport;
  jobId: string;
  council: ReviewerCouncilItem[];
  findingById: Map<string, Finding>;
  ep: EvidencePack;
  sections: SectionReview[];
}) {
  const [open, setOpen] = useState(false);
  const refCount = ep.references.length;

  return (
    <section data-testid="cockpit-layer-3" className="flex flex-col gap-4">
      <button
        type="button"
        data-testid="layer3-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center justify-between gap-3 rounded-md border border-rule-soft bg-bg-card px-4 py-3 text-left transition-colors hover:border-accent"
      >
        <span className="flex items-center gap-2.5">
          <Layers className="h-4 w-4 text-ink-faint" aria-hidden />
          <span className="flex flex-col">
            <span className="text-[14px] font-medium text-ink">
              Uzman katmanı
            </span>
            <span className="text-[12px] text-ink-mute">
              Hakem heyeti · kanıt paketi ({refCount} kaynak) · bölüm
              değerlendirmesi · künye
            </span>
          </span>
        </span>
        <ChevronDown
          className="h-4 w-4 flex-shrink-0 text-ink-faint transition-transform duration-150"
          style={{ transform: open ? "rotate(180deg)" : undefined }}
          aria-hidden
        />
      </button>

      {open ? (
        <div className="flex flex-col gap-8 border-l border-rule-soft pl-4">
          <ReviewerCouncilSection items={council} findingById={findingById} />
          <CitationIntegritySection ep={ep} />
          <ReferencesTable references={ep.references} />
          <SectionReviewsSection sections={sections} />
          <ProvenanceSeal report={report} jobId={jobId} />
        </div>
      ) : null}
    </section>
  );
}

// --- KATMAN 3: hakem heyeti ------------------------------------------------

function ReviewerCouncilSection({
  items,
  findingById,
}: {
  items: ReviewerCouncilItem[];
  findingById: Map<string, Finding>;
}) {
  return (
    <Section title="Hakem heyeti">
      {items.length === 0 ? (
        <EmptyNote>Hakem heyeti görüşü bulunmuyor.</EmptyNote>
      ) : (
        <ul data-testid="reviewer-council" className="flex flex-col gap-3">
          {items.map((item, i) => (
            <li
              key={`${item.role}-${i}`}
              data-testid="council-item"
              data-role={item.role}
              className="flex flex-col gap-2 rounded-md border border-rule-soft bg-bg-card px-4 py-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-[14px] font-medium text-ink">
                  <Users className="h-4 w-4 text-ink-faint" aria-hidden />
                  {COUNCIL_ROLE_LABELS[item.role]}
                </span>
                {item.stance ? (
                  <span className="rounded-sm bg-bg-soft px-2 py-0.5 text-[11.5px] font-medium text-ink-mute">
                    {item.stance}
                  </span>
                ) : null}
              </div>
              {item.summary ? (
                <p className="text-[13.5px] leading-relaxed text-ink-soft">
                  {item.summary}
                </p>
              ) : null}
              {item.key_objection ? (
                <p className="text-[13px] leading-relaxed text-ink-mute">
                  <span className="font-medium text-ink-soft">Ana itiraz: </span>
                  {item.key_objection}
                </p>
              ) : null}
              <ConfidenceMeter
                value={item.confidence}
                label="Güven"
                className="max-w-xs"
              />
              {item.finding_ids.length > 0 ? (
                <p className="text-[12px] text-ink-faint">
                  İlgili bulgular:{" "}
                  {item.finding_ids
                    .map((id) => findingById.get(id)?.title ?? id)
                    .join(" · ")}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

// --- KATMAN 3: kaynak listesi (G5 — artık render edilir) -------------------

const CITATION_STATUS_META: Record<
  CitationStatus,
  { label: string; token: string }
> = {
  resolved: { label: "Doğrulandı", token: "var(--color-ok)" },
  not_found_in_index: { label: "İndekste yok", token: "var(--color-ink-mute)" },
  fabricated: { label: "Çelişkili", token: "var(--color-danger)" },
  retracted: { label: "Geri çekilmiş", token: "var(--color-warn)" },
};

function ReferencesTable({ references }: { references: ParsedReference[] }) {
  return (
    <Section title="Kaynaklar">
      {references.length === 0 ? (
        <EmptyNote>Ayrıştırılmış kaynak listesi bulunmuyor.</EmptyNote>
      ) : (
        <ul data-testid="references-table" className="flex flex-col divide-y divide-rule-soft">
          {references.map((r) => {
            const meta = CITATION_STATUS_META[r.status];
            return (
              <li
                key={r.index}
                data-testid="reference-row"
                data-status={r.status}
                className="flex flex-col gap-1 py-2.5"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-[13.5px] font-medium leading-snug text-ink">
                    <span className="font-mono-pmid text-ink-faint">
                      [{r.index}]
                    </span>{" "}
                    {r.title ?? r.raw}
                    {r.year ? (
                      <span className="ml-1 font-normal text-ink-mute">
                        ({r.year})
                      </span>
                    ) : null}
                  </span>
                  <span
                    className="flex-shrink-0 rounded-sm border px-2 py-0.5 text-[11px] font-medium"
                    style={{ color: meta.token, borderColor: meta.token }}
                  >
                    {meta.label}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px] text-ink-mute">
                  {r.authors.length > 0 ? <span>{r.authors.join(", ")}</span> : null}
                  {r.venue ? (
                    <span className="text-ink-faint">· {r.venue}</span>
                  ) : null}
                  {r.doi ? (
                    <span className="font-mono-pmid text-ink-faint">· {r.doi}</span>
                  ) : null}
                </div>
                {r.evidence ? (
                  <p className="text-[12px] italic leading-relaxed text-ink-faint">
                    {r.evidence}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}

// --- KATMAN 3: atıf bütünlüğü (badge + bağlam + kapsam + istatistik) --------

function CitationIntegritySection({ ep }: { ep: EvidencePack }) {
  return (
    <Section title="Atıf bütünlüğü">
      <CitationIntegrityBar summary={ep.citation_integrity} />
      <CitationIntegrityBadge summary={ep.citation_integrity} />

      {ep.context_findings.length > 0 ? (
        <div className="mt-5 flex flex-col gap-3">
          <h4 className="text-[13px] font-semibold text-ink-soft">
            Atıf-bağlam bulguları
          </h4>
          <ul className="flex flex-col gap-2.5">
            {ep.context_findings.map((f, i) => (
              <li
                key={i}
                className="rounded-md border border-rule-soft bg-bg-card px-4 py-3"
              >
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <ContextSupportChip support={f.support} />
                  <EvidenceBadge supportLevel={f.support_level} />
                  <span className="font-mono-pmid text-[11px] text-ink-faint">
                    kaynak [{f.ref_index}]
                  </span>
                </div>
                <p className="text-[13.5px] leading-relaxed text-ink-soft">
                  {f.claim}
                </p>
                {f.evidence ? (
                  <p className="mt-1 text-[12.5px] italic leading-relaxed text-ink-mute">
                    {f.evidence}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {ep.coverage_gaps.length > 0 ? (
        <div className="mt-5 flex flex-col gap-3">
          <h4 className="text-[13px] font-semibold text-ink-soft">
            Eksik olabilecek çalışmalar
          </h4>
          <ul className="flex flex-col gap-2">
            {ep.coverage_gaps.map((g, i) => (
              <li
                key={i}
                className="rounded-md border border-rule-soft bg-bg-card px-4 py-3"
              >
                <p className="text-[13.5px] font-medium text-ink">
                  {g.title}
                  {g.year ? (
                    <span className="ml-1.5 font-normal text-ink-mute">
                      ({g.year})
                    </span>
                  ) : null}
                </p>
                <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-mute">
                  {g.reason}
                </p>
                <span className="mt-1 inline-block font-mono-pmid text-[11px] text-ink-faint">
                  {g.cited_by_count} atıf · {g.openalex_id}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {ep.stat_findings.length > 0 ? (
        <div className="mt-5 flex flex-col gap-3">
          <h4 className="text-[13px] font-semibold text-ink-soft">
            İstatistik tutarlılığı
          </h4>
          <ul className="flex flex-col gap-2">
            {ep.stat_findings.map((s, i) => (
              <li
                key={i}
                className="flex items-start gap-2.5 rounded-md border border-rule-soft bg-bg-card px-4 py-2.5"
              >
                <StatStatusDot status={s.status} />
                <div className="min-w-0">
                  <span className="font-mono-pmid text-[12px] text-ink-soft">
                    {s.match_text}
                  </span>
                  {s.reported_p != null && s.computed_p != null ? (
                    <p className="mt-0.5 font-mono-pmid text-[11px] text-ink-faint">
                      bildirilen p={s.reported_p} · hesaplanan p={s.computed_p}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Section>
  );
}

// --- KATMAN 3: bölüm bazında değerlendirme ---------------------------------

function SectionReviewsSection({ sections }: { sections: SectionReview[] }) {
  return (
    <Section title="Bölüm bazında değerlendirme">
      {sections.length === 0 ? (
        <EmptyNote>Bölüm bazında değerlendirme bulunmuyor.</EmptyNote>
      ) : (
        <ul data-testid="section-reviews" className="flex flex-col gap-2.5">
          {sections.map((s, i) => {
            const meta = SECTION_STATUS_META[s.status];
            return (
              <li
                key={`${s.section}-${i}`}
                data-testid="section-review"
                data-status={s.status}
                className="flex flex-col gap-1.5 rounded-md border border-rule-soft bg-bg-card px-4 py-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[14px] font-medium text-ink">
                    {s.section}
                  </span>
                  <span
                    className="rounded-sm border px-2 py-0.5 text-[11.5px] font-medium"
                    style={{ color: meta.token, borderColor: meta.token }}
                  >
                    {meta.label}
                  </span>
                </div>
                {s.what_works ? (
                  <p className="text-[13px] leading-relaxed text-ink-soft">
                    <span
                      className="font-medium"
                      style={{ color: "var(--color-ok)" }}
                    >
                      İyi:{" "}
                    </span>
                    {s.what_works}
                  </p>
                ) : null}
                {s.what_breaks ? (
                  <p className="text-[13px] leading-relaxed text-ink-soft">
                    <span
                      className="font-medium"
                      style={{ color: "var(--color-warn)" }}
                    >
                      Sorun:{" "}
                    </span>
                    {s.what_breaks}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}

// ===========================================================================
// v1 RAPOR — v2 alanları yoksa eski düzen birebir korunur (geri-uyum)
// ===========================================================================

function V1Report({ report, jobId }: { report: ReviewReport; jobId: string }) {
  const ep = report.evidence_pack;
  const title = report.manuscript_meta.title ?? "Başlıksız makale";

  return (
    <div className="flex flex-col gap-8">
      <VerdictHeader
        verdict={report.verdict}
        finalScore={report.final_score}
        title={title}
      />

      <EthicsNotice report={report} />
      <EditorDigest report={report} />

      <Section title="Özet">
        <p className="serif max-w-[70ch] text-[15px] leading-relaxed text-ink-soft">
          {report.summary}
        </p>
      </Section>

      {report.dimension_scores.length > 0 ? (
        <Section title="Boyut değerlendirmesi">
          <ul className="flex flex-col divide-y divide-rule-soft">
            {report.dimension_scores.map((d) => (
              <DimensionRow key={d.key} dimension={d} />
            ))}
          </ul>
        </Section>
      ) : null}

      <div className="grid gap-6 md:grid-cols-2">
        {report.strengths.length > 0 ? (
          <GroupedColumn
            heading="Güçlü yönler"
            groups={report.strengths}
            tone="ok"
          />
        ) : null}
        {report.weaknesses.length > 0 ? (
          <GroupedColumn
            heading="Geliştirilecek yönler"
            groups={report.weaknesses}
            tone="warn"
          />
        ) : null}
      </div>

      {report.detailed_comments.length > 0 ? (
        <Section title="Detaylı yorumlar">
          <ul className="flex flex-col gap-4">
            {report.detailed_comments.map((c, i) => (
              <li key={i} className="flex flex-col gap-1">
                <span className="font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-ink-faint">
                  {c.area}
                </span>
                <p className="max-w-[70ch] text-[14px] leading-relaxed text-ink-soft">
                  {c.comment}
                </p>
                {c.evidence_ref ? (
                  <span className="font-mono-pmid text-[11px] text-ink-faint">
                    Kanıt: {c.evidence_ref}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {report.questions.length > 0 ? (
        <Section title="Yazara sorular">
          <ol className="flex flex-col gap-2.5">
            {report.questions.map((q, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="mt-0.5 flex-shrink-0">
                  <HelpCircle className="h-4 w-4 text-ink-faint" aria-hidden />
                </span>
                <span className="max-w-[68ch] text-[14px] leading-relaxed text-ink-soft">
                  {q}
                </span>
              </li>
            ))}
          </ol>
        </Section>
      ) : null}

      <Section title="Genel değerlendirme">
        <p className="serif max-w-[70ch] text-[15px] leading-relaxed text-ink-soft">
          {report.overall_assessment}
        </p>
      </Section>

      <CitationIntegritySection ep={ep} />

      <ProvenanceSeal report={report} jobId={jobId} />
    </div>
  );
}

// --- VERDICT header (v1) ----------------------------------------------------

function VerdictHeader({
  verdict,
  finalScore,
  title,
}: {
  verdict: Verdict;
  finalScore: number | null;
  title: string;
}) {
  const token = VERDICT_TOKEN[verdict];
  return (
    <header className="flex flex-col gap-4 border-b border-rule pb-6">
      <p className="font-mono-pmid text-[11px] uppercase tracking-[0.12em] text-ink-faint">
        Hakem kararı
      </p>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="serif text-[40px] font-medium leading-none tracking-[-0.02em]">
          <span style={{ color: token.color }}>{VERDICT_LABELS[verdict]}</span>
        </h1>
        {finalScore != null ? (
          <div className="flex items-baseline gap-1.5">
            <span
              className="font-mono-pmid text-[32px] font-medium tabular-nums leading-none"
              style={{ color: "var(--color-ink)" }}
            >
              {finalScore.toFixed(1)}
            </span>
            <span className="font-mono-pmid text-[14px] text-ink-faint">
              / 10
            </span>
          </div>
        ) : null}
      </div>
      <p className="max-w-[70ch] text-[14px] leading-relaxed text-ink-mute">
        {title}
      </p>
    </header>
  );
}

// --- paylaşılan: etik uyarısı + editör digesti (v1 + kokpit) ---------------

function EthicsNotice({ report }: { report: ReviewReport }) {
  if (!report.ethics_notice) return null;
  if (report.mode === "editor") {
    return (
      <div
        className="flex items-start gap-3 rounded-md border-l-2 px-4 py-3.5"
        style={{
          borderColor: "var(--color-warn)",
          background: "var(--color-warn-pale)",
        }}
        role="note"
      >
        <ShieldAlert
          className="mt-0.5 h-5 w-5 flex-shrink-0"
          style={{ color: "var(--color-warn)" }}
          aria-hidden
        />
        <div className="flex flex-col gap-1">
          <p
            className="text-[12px] font-semibold uppercase tracking-wider"
            style={{ color: "var(--color-warn)" }}
          >
            Editör modu — sorumluluk uyarısı
          </p>
          <p className="text-[13px] leading-relaxed text-ink-soft">
            {report.ethics_notice}
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-2.5 rounded-md border border-rule-soft bg-bg-card px-4 py-2.5">
      <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-faint" aria-hidden />
      <p className="text-[12.5px] leading-relaxed text-ink-mute">
        {report.ethics_notice}
      </p>
    </div>
  );
}

function EditorDigest({ report }: { report: ReviewReport }) {
  if (!report.editor_digest) return null;
  return (
    <section
      className="flex flex-col gap-2 rounded-md border px-5 py-4"
      style={{
        borderColor: "var(--color-rule)",
        background: "var(--color-bg-soft)",
      }}
    >
      <h2 className="flex items-center gap-2 font-mono-pmid text-[11px] uppercase tracking-[0.1em] text-ink-faint">
        <Gavel className="h-3.5 w-3.5" aria-hidden />
        Editör için karar desteği
      </h2>
      <p className="serif max-w-[72ch] text-[15px] leading-relaxed text-ink">
        {report.editor_digest}
      </p>
    </section>
  );
}

// --- alt bileşenler --------------------------------------------------------

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="serif text-[20px] font-medium italic text-ink">{title}</h2>
      {children}
    </section>
  );
}

function DimensionRow({
  dimension,
}: {
  dimension: { key: keyof typeof DIMENSION_LABELS; score: number; rationale: string };
}) {
  const pct = Math.min(100, Math.max(0, (dimension.score / 10) * 100));
  return (
    <li className="flex flex-col gap-1.5 py-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[14px] font-medium text-ink">
          {DIMENSION_LABELS[dimension.key]}
        </span>
        <span className="font-mono-pmid text-[13px] tabular-nums text-ink-soft">
          {dimension.score.toFixed(1)}
        </span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded-full bg-bg-hover">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, background: "var(--color-ink-faint)" }}
        />
      </div>
      <p className="max-w-[68ch] text-[13px] leading-relaxed text-ink-mute">
        {dimension.rationale}
      </p>
    </li>
  );
}

function GroupedColumn({
  heading,
  groups,
  tone,
}: {
  heading: string;
  groups: { category: string; points: string[] }[];
  tone: "ok" | "warn";
}) {
  const color = tone === "ok" ? "var(--color-ok)" : "var(--color-warn)";
  return (
    <section className="flex flex-col gap-4">
      <h2 className="serif text-[20px] font-medium italic text-ink">{heading}</h2>
      <div className="flex flex-col gap-4">
        {groups.map((g, gi) => (
          <div key={gi} className="flex flex-col gap-1.5">
            <h3
              className="text-[12.5px] font-semibold uppercase tracking-wider"
              style={{ color }}
            >
              {g.category}
            </h3>
            <ul className="flex flex-col gap-1.5">
              {g.points.map((p, pi) => (
                <li
                  key={pi}
                  className="flex gap-2 text-[13.5px] leading-relaxed text-ink-soft"
                >
                  <span
                    aria-hidden
                    className="mt-[7px] h-1 w-1 flex-shrink-0 rounded-full"
                    style={{ background: color }}
                  />
                  {p}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

// --- atıf bütünlüğü — paylaşılan durum listesi (rozet + çubuk reuse eder) --

type CitationSummary = {
  total: number;
  resolved: number;
  not_found_in_index: number;
  fabricated: number;
  retracted: number;
};

type CitationStatusItem = {
  key: CitationStatus | "resolved";
  label: string;
  count: number;
  color: string;
  pale: string;
  icon: React.ReactNode;
};

function citationStatusItems(summary: CitationSummary): CitationStatusItem[] {
  return [
    {
      key: "resolved",
      label: "Doğrulandı",
      count: summary.resolved,
      color: "var(--color-ok)",
      pale: "var(--color-ok-pale)",
      icon: <CheckCircle2 className="h-4 w-4" aria-hidden />,
    },
    {
      key: "not_found_in_index",
      label: "İndekste bulunamadı",
      count: summary.not_found_in_index,
      color: "var(--color-ink-mute)",
      pale: "var(--color-bg-soft)",
      icon: <MinusCircle className="h-4 w-4" aria-hidden />,
    },
    {
      key: "retracted",
      label: "Geri çekilmiş",
      count: summary.retracted,
      color: "var(--color-warn)",
      pale: "var(--color-warn-pale)",
      icon: <AlertCircle className="h-4 w-4" aria-hidden />,
    },
    {
      key: "fabricated",
      label: "Çelişkili kaynak",
      count: summary.fabricated,
      color: "var(--color-danger)",
      pale: "var(--color-danger-pale)",
      icon: <XCircle className="h-4 w-4" aria-hidden />,
    },
  ];
}

// --- atıf bütünlüğü çubuğu (ATIF_BUTUNLUGU_GRAFIGI_2026-08-17) -------------
// dataviz skill kararı: parça-bütün → stacked bar (pasta DEĞİL, anti-patterns:
// "yakın değerleri kıyaslamak için donut/pasta kullanma"). Renkler YENİ İCAT
// EDİLMEDİ — citationStatusItems'ın (yukarıda, rozetle PAYLAŞILAN) status
// renkleri reuse edildi. 2px surface-gap (gap-0.5) segmentleri ayırır, dış
// uçlar rounded-full+overflow-hidden ile yuvarlanır, iç sınırlar kare kalır.
// Yeni kütüphane YOK — d3 projede var ama sadece pre-pivot karmaşık
// görselleştirmelerde (plan §3), bu statik çubuk için gereksiz.

function CitationIntegrityBar({ summary }: { summary: CitationSummary }) {
  if (summary.total === 0) return null;
  const items = citationStatusItems(summary).filter((it) => it.count > 0);

  return (
    <div
      data-testid="citation-integrity-bar"
      role="img"
      aria-label={`${summary.total} kaynaktan ${summary.resolved} doğrulandı, ${summary.not_found_in_index} indekste bulunamadı, ${summary.retracted} geri çekilmiş, ${summary.fabricated} çelişkili kaynak.`}
      className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full"
      style={{ background: "var(--color-bg-soft)" }}
    >
      {items.map((it) => (
        <div
          key={it.key}
          data-testid="citation-integrity-bar-segment"
          data-status={it.key}
          title={`${it.label}: ${it.count}`}
          style={{
            width: `${(it.count / summary.total) * 100}%`,
            background: it.color,
          }}
        />
      ))}
    </div>
  );
}

// --- atıf bütünlüğü rozeti (suçlama tonu YOK) ------------------------------

function CitationIntegrityBadge({ summary }: { summary: CitationSummary }) {
  const items = citationStatusItems(summary);

  return (
    <div className="flex flex-col gap-3">
      <p className="font-mono-pmid text-[12px] text-ink-mute">
        {summary.total} kaynak incelendi
      </p>
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {items.map((it) => (
          <div
            key={it.key}
            className="flex flex-col gap-1.5 rounded-md border px-3 py-2.5"
            style={{
              borderColor: it.count > 0 ? it.color : "var(--color-rule-soft)",
              background: it.count > 0 ? it.pale : "var(--color-bg-card)",
            }}
          >
            <span
              className="flex items-center gap-1.5"
              style={{ color: it.count > 0 ? it.color : "var(--color-ink-faint)" }}
            >
              {it.icon}
              <span className="font-mono-pmid text-[18px] tabular-nums">
                {it.count}
              </span>
            </span>
            <span className="text-[11.5px] leading-tight text-ink-mute">
              {it.label}
            </span>
          </div>
        ))}
      </div>
      <p className="text-[12px] leading-relaxed text-ink-faint">
        &ldquo;İndekste bulunamadı&rdquo; bir suçlama değildir: kaynak OpenAlex/S2
        dizininde eşlenememiştir. Yalnız &ldquo;çelişkili kaynak&rdquo; pozitif bir
        çelişki kanıtına dayanır.
      </p>
    </div>
  );
}

function ContextSupportChip({ support }: { support: ContextSupport }) {
  const map: Record<
    ContextSupport,
    { label: string; color: string; pale: string }
  > = {
    supported: {
      label: "Destekleniyor",
      color: "var(--color-ok)",
      pale: "var(--color-ok-pale)",
    },
    contradicted: {
      label: "Çelişiyor",
      color: "var(--color-danger)",
      pale: "var(--color-danger-pale)",
    },
    unverifiable_from_abstract: {
      label: "Özetten teyit edilemedi",
      color: "var(--color-ink-mute)",
      pale: "var(--color-bg-soft)",
    },
  };
  const m = map[support];
  return (
    <span
      className="rounded-sm px-2 py-0.5 text-[11px] font-medium"
      style={{ background: m.pale, color: m.color }}
    >
      {m.label}
    </span>
  );
}

function StatStatusDot({ status }: { status: "green" | "yellow" | "red" }) {
  const color =
    status === "green"
      ? "var(--color-ok)"
      : status === "yellow"
        ? "var(--color-warn)"
        : "var(--color-danger)";
  return (
    <span
      aria-hidden
      className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full"
      style={{ background: color }}
    />
  );
}

// --- künye / provenance seal (küratörlü, açılır) ---------------------------

function ProvenanceSeal({
  report,
  jobId,
}: {
  report: ReviewReport;
  jobId: string;
}) {
  const [open, setOpen] = useState(false);
  const p = report.provenance;
  const when = new Date(p.generated_at);
  const whenLabel = Number.isNaN(when.getTime())
    ? p.generated_at
    : when.toLocaleString("tr-TR");

  return (
    <footer className="mt-2 border-t border-rule pt-4">
      <div className="flex items-center gap-3">
        <span
          aria-hidden
          className="h-3 w-[2px] flex-shrink-0 rounded-full"
          style={{ background: "var(--color-accent)" }}
        />
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex flex-1 items-center justify-between gap-2 text-left"
        >
          <span className="flex items-center gap-2 font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-ink-faint">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
            {jobId.slice(0, 8)} · {p.engine_version} ·{" "}
            {p.deterministic_engine ? "deterministik motor" : "motor"} · künye
          </span>
          <ChevronDown
            className="h-3.5 w-3.5 flex-shrink-0 text-ink-faint transition-transform duration-150"
            style={{ transform: open ? "rotate(180deg)" : undefined }}
            aria-hidden
          />
        </button>
      </div>

      {open ? (
        <dl className="mt-3 grid gap-x-6 gap-y-1.5 pl-5 sm:grid-cols-2">
          <ProvRow label="Üreten" value={`${BRAND} tarafından üretildi`} />
          <ProvRow label="İş kimliği" value={jobId} />
          <ProvRow label="Model" value={p.model_used} />
          <ProvRow label="Persona sürümü" value={p.persona_version} />
          <ProvRow label="Motor sürümü" value={p.engine_version} />
          <ProvRow label="Üretildi" value={whenLabel} />
          <ProvRow
            label="Olgu katmanı"
            value={
              p.deterministic_engine
                ? "Deterministik (atıf/istatistik/kapsam bit-kararlı)"
                : "Belirsiz"
            }
          />
          <ProvRow
            label="Yargı katmanı"
            value={
              p.judgment_reproducible
                ? "Yeniden üretilebilir"
                : "LLM yargısı bit-kararlı değildir (dürüst işaret)"
            }
          />
        </dl>
      ) : null}
    </footer>
  );
}

function ProvRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-ink-faint">
        {label}
      </dt>
      <dd className="font-mono-pmid text-[12px] text-ink-mute">{value}</dd>
    </div>
  );
}

// ===========================================================================
// etiket sözlükleri (çıplak enum yerine son-kullanıcı dili)
// ===========================================================================

const COUNCIL_ROLE_LABELS: Record<CouncilRole, string> = {
  methodologist: "Yöntem uzmanı",
  field_expert: "Alan uzmanı",
  skeptical_reviewer: "Şüpheci hakem",
  constructive_reviewer: "Yapıcı hakem",
  citation_auditor: "Atıf denetçisi",
  ethics_reviewer: "Etik hakemi",
  statistics_reviewer: "İstatistik hakemi",
  editor_synthesizer: "Editör sentezi",
};

const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  journal_article: "Dergi makalesi",
  conference_paper: "Konferans bildirisi",
  thesis: "Tez",
  grant_proposal: "Proje önerisi",
  preprint: "Ön baskı",
  technical_report: "Teknik rapor",
  book_chapter: "Kitap bölümü",
  unknown: "Belirsiz tür",
};

const STUDY_DESIGN_LABELS: Record<StudyDesign, string> = {
  qualitative: "Nitel",
  quantitative: "Nicel",
  mixed_methods: "Karma yöntem",
  systematic_review: "Sistematik derleme",
  meta_analysis: "Meta-analiz",
  scoping_review: "Kapsam derlemesi",
  theoretical: "Kuramsal",
  conceptual: "Kavramsal",
  design_science: "Tasarım bilimi",
  computational_modeling: "Hesaplamalı modelleme",
  dataset_resource: "Veri seti kaynağı",
  software_tool: "Yazılım aracı",
  replication: "Yineleme",
  registered_report: "Kayıtlı rapor",
  case_study: "Vaka çalışması",
  protocol: "Protokol",
  unknown: "Belirsiz tasarım",
};

// risk_radar.dimension serbest string'dir; spec radar boyutları + v1 boyut
// anahtarları birlikte humanize edilir, eşleşmezse ham string gösterilir.
const RADAR_DIM_LABELS: Record<string, string> = {
  contribution: "Katkı",
  literature: "Literatür",
  methodology: "Yöntem",
  evidence: "Kanıt",
  citation: "Atıf",
  statistics: "İstatistik",
  ethics: "Etik",
  reproducibility: "Yinelenebilirlik",
  writing: "Yazım",
  venue_fit: "Dergi uygunluğu",
};

function humanizeDimension(dim: string): string {
  return (
    (DIMENSION_LABELS as Record<string, string>)[dim] ??
    RADAR_DIM_LABELS[dim] ??
    dim
  );
}

const SECTION_STATUS_META: Record<
  SectionReview["status"],
  { label: string; token: string }
> = {
  ok: { label: "Sağlam", token: "var(--color-ok)" },
  weak: { label: "Zayıf", token: "var(--color-warn)" },
  broken: { label: "Sorunlu", token: "var(--color-danger)" },
  missing: { label: "Eksik", token: "var(--color-ink-mute)" },
};

const SEVERITY_RANK: Record<Finding["severity"], number> = {
  critical: 0,
  major: 1,
  moderate: 2,
  minor: 3,
  info: 4,
};

// --- ortak boş-durum notu (beyaz boşluk yerine dürüst hal) -----------------

function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <p
      data-testid="empty-note"
      className="rounded-md border border-dashed border-rule-soft bg-bg-card px-4 py-3 text-[13px] text-ink-mute"
    >
      {children}
    </p>
  );
}

// --- şeffaflık alt-bilgisi (AI kullanım açıklaması) ------------------------

const CONFIDENTIALITY_LABELS: Record<
  AIUsageDisclosure["confidentiality_mode"],
  string
> = {
  author_owned: "Yazar sahipliği",
  reviewer_confidential: "Hakem gizliliği",
};

function DisclosureFooter({ disclosure }: { disclosure: AIUsageDisclosure }) {
  return (
    <section
      data-testid="disclosure-footer"
      className="flex flex-col gap-2.5 rounded-md border border-rule-soft bg-bg-soft px-5 py-4"
    >
      <h2 className="flex items-center gap-2 font-mono-pmid text-[11px] uppercase tracking-[0.1em] text-ink-faint">
        <Sparkles className="h-3.5 w-3.5" aria-hidden />
        Şeffaflık · Yapay zekâ kullanımı
      </h2>
      <dl className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
        <ProvRow
          label="Harici yapay zekâ"
          value={disclosure.external_ai_used ? "Kullanıldı" : "Kullanılmadı"}
        />
        <ProvRow
          label="Sağlayıcılar"
          value={
            disclosure.providers.length > 0
              ? disclosure.providers.join(", ")
              : "—"
          }
        />
        <ProvRow
          label="Gizlilik kipi"
          value={CONFIDENTIALITY_LABELS[disclosure.confidentiality_mode]}
        />
        <ProvRow
          label="Onay durumu"
          value={
            disclosure.degraded_due_to_consent
              ? "Onay kısıtı nedeniyle sınırlı"
              : "Tam"
          }
        />
      </dl>
      {disclosure.degraded_due_to_consent ? (
        <DegradedNotice
          reason={
            disclosure.note ??
            "Harici yapay zekâ onayı verilmediği için rapor sınırlı üretildi."
          }
        />
      ) : disclosure.note ? (
        <p className="text-[12.5px] leading-relaxed text-ink-mute">
          {disclosure.note}
        </p>
      ) : null}
    </section>
  );
}

// --- çıpa drawer (bulgu → makaledeki yer + alıntı) -------------------------

function AnchorDrawer({
  anchor,
  onClose,
}: {
  anchor: ManuscriptAnchor | null;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const isOpen = anchor != null;

  // odak yönetimi (isOpen kenarına bağlı — onClose kimliği değişse de yeniden tetiklenmez):
  // açılışta tetikleyiciyi sakla + odağı dialog'a al; kapanışta odağı tetikleyiciye iade et (WCAG 2.2 AA)
  useEffect(() => {
    if (!isOpen) return;
    triggerRef.current = document.activeElement as HTMLElement | null;
    closeBtnRef.current?.focus();
    return () => {
      triggerRef.current?.focus?.();
    };
  }, [isOpen]);

  // Esc kapatır + Tab focus-trap (odak dialog içinde döner, arka plana kaçmaz)
  useEffect(() => {
    if (!isOpen) return;
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
  }, [isOpen, onClose]);

  if (!anchor) return null;

  const section = anchor.section ?? "Makale";

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Kapat"
        onClick={onClose}
        className="absolute inset-0 bg-ink/30"
      />
      <aside
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`${section} bölümünden alıntı`}
        data-testid="anchor-drawer"
        className="relative flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto border-l border-rule bg-bg-card px-6 py-6 shadow-lg"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <span className="font-mono-pmid text-[11px] uppercase tracking-[0.1em] text-ink-faint">
              Makaledeki yer
            </span>
            <h2 className="serif text-[20px] font-medium text-ink">{section}</h2>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="rounded-md p-1.5 text-ink-faint transition-colors hover:bg-bg-hover hover:text-ink"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        {anchor.quote ? (
          <blockquote
            data-testid="anchor-quote"
            className="serif border-l-2 px-4 py-2 text-[14.5px] leading-relaxed text-ink-soft"
            style={{ borderColor: "var(--color-accent)" }}
          >
            “{anchor.quote}”
          </blockquote>
        ) : (
          <p className="text-[13px] text-ink-mute">
            Bu çıpa için alıntı metni bulunmuyor.
          </p>
        )}

        <span className="font-mono-pmid text-[11px] text-ink-faint">
          çıpa: {anchor.anchor_id}
        </span>
      </aside>
    </div>
  );
}
