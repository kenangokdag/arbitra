// F-E2 — ReviewReportView VERDICT KOKPİTİ testleri (DESIGN-DECISIONS §5).
// "Gördüm" kanıtı: fixture'ı render edip 3 katmanın da göründüğünü + İMZA ANI
// drill'ini (risk → bulgu → çıpa → düzeltme) assert ederiz (browser yok).
// 5 UX durumu: dolu-v2 · v1-geriye-uyum · rıza-düşürülmüş · boş-dizi · drawer.

import { afterEach, describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReviewReportView } from "./ReviewReportView";
import { REPORT_V2_DEMO } from "@/fixtures/report-v2-demo";
import type { ReviewReport } from "@/lib/review-api";
import { initialUiState, useUiStore } from "@/stores/ui";

const JOB = "demo-job-1234abcd";

describe("ReviewReportView — v2 kokpit, 3 katman", () => {
  it("Katman 1/2/3'ün hepsi render edilir (verdict-önce omurga)", () => {
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    // KATMAN 1 — verdict (karar EN İRİ + hazırlık skoru teşhisin altında)
    expect(screen.getByTestId("cockpit-layer-1")).toBeInTheDocument();
    expect(screen.getByTestId("executive-verdict")).toBeInTheDocument();
    expect(screen.getByTestId("exec-decision")).toHaveTextContent("Büyük revizyon");
    expect(screen.getByTestId("exec-readiness")).toHaveTextContent("66");
    expect(screen.getByTestId("top-fatal-risks")).toBeInTheDocument();

    // KATMAN 2 — risk radarı (severity-sıralı; en kritik üstte)
    expect(screen.getByTestId("cockpit-layer-2")).toBeInTheDocument();
    const radar = screen.getByTestId("risk-radar");
    expect(within(radar).getByText("Yöntem sağlamlığı")).toBeInTheDocument();
    // critical (soundness) ilk sırada olmalı (severity-sıralı)
    const items = screen.getAllByTestId("risk-radar-item");
    expect(items[0]).toHaveAttribute("data-dimension", "soundness");

    // KATMAN 3 — uzman katmanı VARSAYILAN KAPALI (bağırmaz)
    expect(screen.getByTestId("cockpit-layer-3")).toBeInTheDocument();
    expect(screen.queryByTestId("reviewer-council")).toBeNull();
    expect(screen.queryByTestId("references-table")).toBeNull();

    // Şeffaflık (disclosure) — her zaman görünür (§7)
    expect(screen.getByTestId("disclosure-footer")).toBeInTheDocument();
  });

  it("İMZA ANI: risk'e tıkla → bulgu + çıpa + düzeltme açılır; çıpa → drawer alıntı", async () => {
    const user = userEvent.setup();
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    // Drill başta KAPALI: bulgu/çıpa görünmüyor (talep-üzerine açığa çıkarma)
    expect(
      screen.queryByText("Güç analizi ve örneklem gerekçesi eksik"),
    ).toBeNull();
    expect(screen.queryAllByTestId("manuscript-anchor-link")).toHaveLength(0);

    // En kritik riske (Yöntem sağlamlığı = soundness) tıkla → drill açılır
    await user.click(within(screen.getByTestId("risk-radar")).getByText("Yöntem sağlamlığı"));

    // bağlı bulgu görünür
    const findingCard = screen.getByTestId("finding-card");
    expect(
      within(findingCard).getByText("Güç analizi ve örneklem gerekçesi eksik"),
    ).toBeInTheDocument();

    // 2B — bağlı düzeltme (action_item) aynı kartta görünür (risk→bulgu→fix iplik)
    expect(within(findingCard).getByTestId("finding-fix")).toBeInTheDocument();
    expect(
      within(findingCard).getByText(
        /Örneklem büyüklüğünün nasıl belirlendiğini açıklayın/,
      ),
    ).toBeInTheDocument();

    // İMZA ANI — çıpaya tıkla → makaledeki tam cümle drawer'da
    expect(screen.queryByTestId("anchor-drawer")).toBeNull();
    const anchor = within(findingCard).getByTestId("manuscript-anchor-link");
    await user.click(anchor);

    expect(screen.getByTestId("anchor-drawer")).toBeInTheDocument();
    expect(screen.getByTestId("anchor-quote")).toHaveTextContent(
      "Toplam 84 katılımcı çalışmaya dahil edildi.",
    );
  });

  it("AnchorDrawer a11y: Esc kapatır + odak çıpaya geri döner (WCAG 2.2 AA)", async () => {
    const user = userEvent.setup();
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    await user.click(within(screen.getByTestId("risk-radar")).getByText("Yöntem sağlamlığı"));
    const findingCard = screen.getByTestId("finding-card");
    const anchor = within(findingCard).getByTestId("manuscript-anchor-link");
    await user.click(anchor);
    expect(screen.getByTestId("anchor-drawer")).toBeInTheDocument();

    // Esc → drawer kapanır
    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("anchor-drawer")).toBeNull();

    // odak-iadesi: kapanınca odak, drawer'ı açan çıpaya döner (arka planda kaybolmaz)
    expect(anchor).toHaveFocus();
  });

  it("Katman 3 açılınca hakem heyeti + kanıt paketi + kaynak tablosu (G5) görünür", async () => {
    const user = userEvent.setup();
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    await user.click(screen.getByTestId("layer3-toggle"));

    // hakem heyeti
    const council = screen.getByTestId("reviewer-council");
    expect(within(council).getByText("Yöntem uzmanı")).toBeInTheDocument();

    // kanıt paketi — EvidenceBadge (support_level) canlı
    const badge = screen.getByTestId("evidence-badge");
    expect(badge).toHaveAttribute("data-support-level", "abstract_only");
    expect(badge).toHaveTextContent("Yalnızca özetten");

    // G5 — kaynak tablosu artık render edilir
    const refs = screen.getByTestId("references-table");
    expect(
      within(refs).getByText("Remote work and team output"),
    ).toBeInTheDocument();
    // geri çekilmiş kaynak statü rozetiyle görünür
    expect(within(refs).getByText("Geri çekilmiş")).toBeInTheDocument();

    // bölüm bazında değerlendirme
    const secReviews = screen.getByTestId("section-reviews");
    expect(within(secReviews).getByText("Yöntem")).toBeInTheDocument();
  });
});

describe("ReviewReportView — v1 geriye-uyum", () => {
  it("v2 alanları olmayan rapor eskisi gibi render edilir, kokpit çıkmaz", () => {
    const {
      schema_version: _sv,
      document_classification: _dc,
      executive_verdict: _ev,
      risk_radar: _rr,
      reviewer_council: _rc,
      findings: _f,
      action_plan: _ap,
      section_reviews: _sr,
      disclosure: _d,
      ...v1
    } = REPORT_V2_DEMO;

    render(<ReviewReportView report={v1 as ReviewReport} jobId={JOB} />);

    // v1 içerik var
    expect(
      screen.getByText(/Çalışma güçlü bir araştırma sorusu sunuyor/),
    ).toBeInTheDocument();

    // kokpit katmanları YOK
    expect(screen.queryByTestId("cockpit-layer-1")).toBeNull();
    expect(screen.queryByTestId("executive-verdict")).toBeNull();
    expect(screen.queryByTestId("risk-radar")).toBeNull();
    expect(screen.queryByTestId("disclosure-footer")).toBeNull();
  });
});

describe("ReviewReportView — rıza nedeniyle düşürülmüş rapor", () => {
  const degraded: ReviewReport = {
    ...REPORT_V2_DEMO,
    schema_version: "review_report.v2",
    document_classification: null,
    executive_verdict: null,
    risk_radar: [],
    reviewer_council: [],
    findings: [],
    action_plan: [],
    section_reviews: [],
    disclosure: {
      external_ai_used: false,
      providers: [],
      confidentiality_mode: "reviewer_confidential",
      degraded_due_to_consent: true,
      note: "Harici yapay zekâ onayı verilmediği için rapor sınırlı üretildi.",
    },
  };

  it("beyaz ekran yerine DegradedNotice + dürüst boş durumlar gösterir, çökmez", () => {
    render(<ReviewReportView report={degraded} jobId={JOB} />);

    // en az bir düşürülme uyarısı (katman-1 + disclosure footer)
    expect(
      screen.getAllByTestId("degraded-notice").length,
    ).toBeGreaterThanOrEqual(1);

    // karar yine de dürüstçe gösterilir (fallback verdict)
    expect(screen.getByTestId("exec-decision")).toHaveTextContent("Büyük revizyon");

    // katman-2 dürüst boş durum (sessiz beyaz değil)
    expect(
      screen.getByText("Boyut riski hesaplanmadı, bulgu kaydedilmedi."),
    ).toBeInTheDocument();

    // disclosure footer yine görünür
    expect(screen.getByTestId("disclosure-footer")).toBeInTheDocument();
  });
});

describe("ReviewReportView — testid temizliği (auditor notu)", () => {
  it("drill listesi 'findings' iken 'diğer bulgular' AYRI testid 'findings-other' kullanır", async () => {
    const user = userEvent.setup();
    // risk_radar'da OLMAYAN bir boyutta bulgu ekle → leftover ("diğer bulgular") render olur.
    const withLeftover: ReviewReport = {
      ...REPORT_V2_DEMO,
      findings: [
        ...(REPORT_V2_DEMO.findings ?? []),
        {
          finding_id: "F-LEFTOVER",
          dimension: "ethics", // risk_radar'da yok → leftover
          severity: "minor",
          confidence: 0.5,
          title: "Etik beyanı bulunamadı",
          summary: "Veri toplama izni belirtilmemiş.",
          manuscript_anchors: [],
          reasoning_public: null,
          limitations: [],
          action_item_ids: [],
          global_issue: false,
        },
      ],
    };

    render(<ReviewReportView report={withLeftover} jobId={JOB} />);

    // leftover listesi AYRI testid ile TEK (duplicate olsaydı getByTestId patlardı)
    const other = screen.getByTestId("findings-other");
    expect(
      within(other).getByText("Etik beyanı bulunamadı"),
    ).toBeInTheDocument();

    // drill 'findings' testid'i leftover'dan ayrı — drill kapalıyken yok, açınca TEK
    expect(screen.queryByTestId("findings")).toBeNull();
    await user.click(within(screen.getByTestId("risk-radar")).getByText("Yöntem sağlamlığı"));
    expect(screen.getByTestId("findings")).toBeInTheDocument();
  });
});

describe("ReviewReportView — boş bulgu dizisi", () => {
  it("findings boş ise risk satırı 'bağlı bulgu yok' der, çökmez", () => {
    const report: ReviewReport = { ...REPORT_V2_DEMO, findings: [] };
    render(<ReviewReportView report={report} jobId={JOB} />);
    // her risk satırı drill'siz → dürüst not
    expect(
      screen.getAllByText("Bu boyut için bağlı bulgu yok.").length,
    ).toBeGreaterThanOrEqual(1);
  });
});

describe("ReviewReportView — atıf bütünlüğü çubuğu (ATIF_BUTUNLUGU_GRAFIGI_2026-08-17)", () => {
  it("segment genişlikleri orantılı, title'da doğru etiket+sayı var (Katman 3 açılınca)", async () => {
    const user = userEvent.setup();
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);
    await user.click(screen.getByTestId("layer3-toggle"));

    const bar = screen.getByTestId("citation-integrity-bar");
    expect(bar).toBeInTheDocument();

    // fixture: total=41, resolved=38, not_found_in_index=2, retracted=1, fabricated=0
    const segments = screen.getAllByTestId("citation-integrity-bar-segment");
    // fabricated=0 → filtrelenir, sadece count>0 olan 3 segment render edilir
    expect(segments).toHaveLength(3);

    const resolvedSeg = segments.find(
      (s) => s.getAttribute("data-status") === "resolved",
    )!;
    expect(resolvedSeg).toHaveAttribute("title", "Doğrulandı: 38");
    expect(resolvedSeg.style.width).toBe(`${(38 / 41) * 100}%`);

    expect(
      segments.find((s) => s.getAttribute("data-status") === "fabricated"),
    ).toBeUndefined();
  });

  it("total=0 iken çubuk render edilmez, çökmez", async () => {
    const user = userEvent.setup();
    const report: ReviewReport = {
      ...REPORT_V2_DEMO,
      evidence_pack: {
        ...REPORT_V2_DEMO.evidence_pack,
        citation_integrity: {
          total: 0,
          resolved: 0,
          not_found_in_index: 0,
          fabricated: 0,
          retracted: 0,
        },
      },
    };
    render(<ReviewReportView report={report} jobId={JOB} />);
    await user.click(screen.getByTestId("layer3-toggle"));
    expect(screen.queryByTestId("citation-integrity-bar")).toBeNull();
  });
});

describe("ReviewReportView — versiyon karşılaştırma özeti (VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17)", () => {
  it("comparison prop verilmezse hiçbir şey render edilmez (mevcut davranış korunur)", () => {
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);
    expect(screen.queryByTestId("version-comparison-summary")).toBeNull();
  });

  it("comparison=null iken hiçbir şey render edilmez", () => {
    render(
      <ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} comparison={null} />,
    );
    expect(screen.queryByTestId("version-comparison-summary")).toBeNull();
  });

  it("verdict değişimi + hazırlık puanı + boyut deltalarını gösterir", () => {
    render(
      <ReviewReportView
        report={REPORT_V2_DEMO}
        jobId={JOB}
        comparison={{
          parent_job_id: "parent-1",
          previous_verdict: "reject",
          current_verdict: "major_revision",
          verdict_changed: true,
          previous_readiness_score: 40,
          current_readiness_score: 66,
          readiness_delta: 26,
          dimension_deltas: [
            { key: "soundness", previous_score: 4, current_score: 6.2, delta: 2.2 },
          ],
        }}
      />,
    );

    const summary = screen.getByTestId("version-comparison-summary");
    expect(within(summary).getByText("Ret")).toBeInTheDocument();
    expect(within(summary).getByText("Büyük revizyon")).toBeInTheDocument();
    expect(within(summary).getByText("40")).toBeInTheDocument();
    expect(within(summary).getByText("66")).toBeInTheDocument();
    expect(within(summary).getByText("(+26)")).toBeInTheDocument();

    const deltas = screen.getByTestId("version-comparison-dimension-deltas");
    expect(within(deltas).getByText("Yöntem sağlamlığı")).toBeInTheDocument();
    expect(within(deltas).getByText("+2.2")).toBeInTheDocument();
  });

  it("verdict AYNIYSA 'Karar aynı' metni gösterir, ok-işareti göstermez", () => {
    render(
      <ReviewReportView
        report={REPORT_V2_DEMO}
        jobId={JOB}
        comparison={{
          parent_job_id: "parent-1",
          previous_verdict: "accept",
          current_verdict: "accept",
          verdict_changed: false,
          previous_readiness_score: null,
          current_readiness_score: null,
          readiness_delta: null,
          dimension_deltas: [],
        }}
      />,
    );
    const summary = screen.getByTestId("version-comparison-summary");
    expect(within(summary).getByText(/Karar aynı/)).toBeInTheDocument();
  });
});

describe("ReviewReportView — Finding kaynak-metin tutarlılığı (FINDING_KAYNAK_ALINTI_TUTARLILIGI_2026-08-16 Katman A)", () => {
  it("anchor'lı Finding'de mevcut davranış korunur (regresyon guard'ı)", async () => {
    const user = userEvent.setup();
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    await user.click(
      within(screen.getByTestId("risk-radar")).getByText("Yöntem sağlamlığı"),
    );
    const findingCard = screen.getByTestId("finding-card");
    expect(
      within(findingCard).getByTestId("manuscript-anchor-link"),
    ).toBeInTheDocument();
    expect(
      within(findingCard).queryByTestId("finding-source-unspecified"),
    ).toBeNull();
    expect(
      within(findingCard).queryByTestId("finding-source-global"),
    ).toBeNull();
  });

  it("anchor'sız + global_issue=false Finding → dürüst 'konum belirtilmedi' notu (F-003, clarity)", async () => {
    const user = userEvent.setup();
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    await user.click(
      within(screen.getByTestId("risk-radar")).getByText("Anlaşılırlık"),
    );
    const findingCard = screen.getByTestId("finding-card");
    expect(
      within(findingCard).getByTestId("finding-source-unspecified"),
    ).toHaveTextContent("Kaynak konumu yapısal olarak belirtilmedi.");
    expect(
      within(findingCard).queryByTestId("manuscript-anchor-link"),
    ).toBeNull();
  });

  it("anchor'sız + global_issue=true Finding → 'belge geneli sorun' etiketi", async () => {
    const user = userEvent.setup();
    const report: ReviewReport = {
      ...REPORT_V2_DEMO,
      findings: (REPORT_V2_DEMO.findings ?? []).map((f) =>
        f.finding_id === "F-003" ? { ...f, global_issue: true } : f,
      ),
    };
    render(<ReviewReportView report={report} jobId={JOB} />);

    await user.click(
      within(screen.getByTestId("risk-radar")).getByText("Anlaşılırlık"),
    );
    const findingCard = screen.getByTestId("finding-card");
    expect(
      within(findingCard).getByTestId("finding-source-global"),
    ).toHaveTextContent(
      "Bu belge geneli bir sorun — tek bir cümleye işaret edilmiyor.",
    );
    expect(
      within(findingCard).queryByTestId("finding-source-unspecified"),
    ).toBeNull();
  });
});

describe("ReviewReportView — sınırlayıcı boyut vurgusu (SINIRLAYICI_BOYUT_VURGUSU_2026-08-16)", () => {
  it("en düşük dimension_score'u (soundness=6.2) + rationale'ını gösterir", () => {
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    const callout = screen.getByTestId("limiting-dimension-callout");
    expect(callout).toHaveAttribute("data-dimension", "soundness");
    expect(within(callout).getByText(/Yöntem sağlamlığı/)).toBeInTheDocument();
    expect(within(callout).getByText(/6\.2 \/ 10/)).toBeInTheDocument();
    expect(
      within(callout).getByText(
        "Güç analizi ve örneklem gerekçesi eksik.",
      ),
    ).toBeInTheDocument();
  });

  it("dimension_scores boşsa callout render edilmez, çökmez", () => {
    const report: ReviewReport = { ...REPORT_V2_DEMO, dimension_scores: [] };
    render(<ReviewReportView report={report} jobId={JOB} />);
    expect(screen.queryByTestId("limiting-dimension-callout")).toBeNull();
  });

  it("berabere durumda 7-radar-bağlantılı boyut (soundness) LLM-yalnız boyuttan (importance) ÖNCELİKLİDİR", () => {
    const report: ReviewReport = {
      ...REPORT_V2_DEMO,
      dimension_scores: [
        { key: "importance", score: 6.2, rationale: "LLM-yalnız gerekçe." },
        { key: "soundness", score: 6.2, rationale: "Radar-bağlantılı gerekçe." },
      ],
    };
    render(<ReviewReportView report={report} jobId={JOB} />);

    const callout = screen.getByTestId("limiting-dimension-callout");
    expect(callout).toHaveAttribute("data-dimension", "soundness");
    expect(within(callout).getByText("Radar-bağlantılı gerekçe.")).toBeInTheDocument();
  });
});

describe("ReviewReportView — öncelikli düzeltme listesi (RAPOR_ONCELIKLI_DUZELTME_LISTESI_2026-08-16)", () => {
  it("Katman 1 ile 2 arasında HER ZAMAN açık; P0 grubu P1'den ÖNCE; bağlı bulgu başlığı görünür", () => {
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    const section = screen.getByTestId("priority-actions");
    expect(section).toBeInTheDocument();

    // grup sırası: P0 önce, P1 sonra (fixture'da 1×P0 + 1×P1 var)
    const groups = screen.getAllByTestId("priority-group");
    expect(groups.map((g) => g.getAttribute("data-priority"))).toEqual([
      "P0",
      "P1",
    ]);

    // P0 grubu → AI-001'in talimatı + bağlı bulgunun (F-001) başlığı
    const p0 = groups[0]!;
    expect(
      within(p0).getByText(
        /Örneklem büyüklüğünün nasıl belirlendiğini açıklayın/,
      ),
    ).toBeInTheDocument();
    expect(
      within(p0).getByText(/Güç analizi ve örneklem gerekçesi eksik/),
    ).toBeInTheDocument();

    // bilinçli tekrar: aynı fix Katman 2'nin drill'i AÇILMADAN da burada görünür
    // (drill kapalı durumda finding-card henüz yok, ama priority-actions'ta var)
    expect(screen.queryByTestId("finding-card")).toBeNull();
  });

  it("action_plan boşsa dürüst EmptyNote gösterir, kart render etmez", () => {
    const report: ReviewReport = { ...REPORT_V2_DEMO, action_plan: [] };
    render(<ReviewReportView report={report} jobId={JOB} />);

    const section = screen.getByTestId("priority-actions");
    expect(
      within(section).getByText(
        "Bu rapor için önceliklendirilmiş bir düzeltme aksiyonu işaretlenmedi.",
      ),
    ).toBeInTheDocument();
    expect(within(section).queryByTestId("action-item-card")).toBeNull();
    expect(screen.queryAllByTestId("priority-group")).toHaveLength(0);
  });
});

describe("ReviewReportView — Danışman tetikleyicisi (DANISMAN_FRONTEND_KABLOLAMA_2026-08-19)", () => {
  afterEach(() => {
    useUiStore.setState(initialUiState);
  });

  it("tıklayınca openChatbox mode='review_advisor' + reportId=jobId ile çağrılır, pageState YOK", async () => {
    const user = userEvent.setup();
    render(<ReviewReportView report={REPORT_V2_DEMO} jobId={JOB} />);

    await user.click(screen.getByTestId("ask-advisor-button"));

    const { context } = useUiStore.getState().chatbox;
    expect(context).toEqual({
      kind: "advisor",
      mode: "review_advisor",
      reportId: JOB,
    });
  });
});
