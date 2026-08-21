"use client";

import { use, useState, Suspense, lazy } from "react";
import { PlaceholderPage } from "@/components/PlaceholderPage";
import { getPageTitle, findWorkbenchInfo } from "@/lib/nav-config";

// ── Lazy-loaded workbench pages ────────────────────────────────────────────
const TopicSuggestionPage   = lazy(() => import("@/components/project/TopicSuggestionPage").then(m => ({ default: m.TopicSuggestionPage })));
const ThematicAnalysisPage  = lazy(() => import("@/components/project/ThematicAnalysisPage").then(m => ({ default: m.ThematicAnalysisPage })));
const ConceptNetworkPage    = lazy(() => import("@/components/project/ConceptNetworkPage").then(m => ({ default: m.ConceptNetworkPage })));
const BibliometricSummaryPage = lazy(() => import("@/components/project/BibliometricSummaryPage").then(m => ({ default: m.BibliometricSummaryPage })));
const ResearchAreaConfirmPage = lazy(() => import("@/components/project/ResearchAreaConfirmPage").then(m => ({ default: m.ResearchAreaConfirmPage })));
const CitationQualityPage   = lazy(() => import("@/components/project/CitationQualityPage").then(m => ({ default: m.CitationQualityPage })));
const ConnectedPapersPage   = lazy(() => import("@/components/project/ConnectedPapersPage").then(m => ({ default: m.ConnectedPapersPage })));
const MethodDataEthicsPage  = lazy(() => import("@/components/project/MethodDataEthicsPage").then(m => ({ default: m.MethodDataEthicsPage })));
const LiteratureSummaryPage = lazy(() => import("@/components/project/LiteratureSummaryPage").then(m => ({ default: m.LiteratureSummaryPage })));
const ExtendedSummaryPage   = lazy(() => import("@/components/project/ExtendedSummaryPage").then(m => ({ default: m.ExtendedSummaryPage })));
const GapHeatmapCard        = lazy(() => import("@/components/project/GapHeatmapCard").then(m => ({ default: m.GapHeatmapCard })));
const GapProfilePage        = lazy(() => import("@/components/project/GapProfilePage").then(m => ({ default: m.GapProfilePage })));
const OriginalityPage       = lazy(() => import("@/components/project/OriginalityPage").then(m => ({ default: m.OriginalityPage })));
const GapComparisonPage     = lazy(() => import("@/components/project/GapComparisonPage").then(m => ({ default: m.GapComparisonPage })));
const ImpactCurvePage       = lazy(() => import("@/components/project/ImpactCurvePage").then(m => ({ default: m.ImpactCurvePage })));
const PublicationTypePage   = lazy(() => import("@/components/project/PublicationTypePage").then(m => ({ default: m.PublicationTypePage })));
const WritingSkeletonPage   = lazy(() => import("@/components/project/WritingSkeletonPage").then(m => ({ default: m.WritingSkeletonPage })));
const AcademicLanguagePage  = lazy(() => import("@/components/project/AcademicLanguagePage").then(m => ({ default: m.AcademicLanguagePage })));
const AnchorRecommendationsPage = lazy(() => import("@/components/project/AnchorRecommendationsPage").then(m => ({ default: m.AnchorRecommendationsPage })));
const DefenseFormatPage     = lazy(() => import("@/components/project/DefenseFormatPage").then(m => ({ default: m.DefenseFormatPage })));
const ThesisContentPage     = lazy(() => import("@/components/project/ThesisContentPage").then(m => ({ default: m.ThesisContentPage })));
const IndividualFeedbackPage = lazy(() => import("@/components/project/IndividualFeedbackPage").then(m => ({ default: m.IndividualFeedbackPage })));
const JournalSimulationPage = lazy(() => import("@/components/project/JournalSimulationPage").then(m => ({ default: m.JournalSimulationPage })));
const ProjectClosurePage    = lazy(() => import("@/components/project/ProjectClosurePage").then(m => ({ default: m.ProjectClosurePage })));
const DiarySidebar          = lazy(() => import("@/components/project/DiarySidebar").then(m => ({ default: m.DiarySidebar })));
const SessionPage           = lazy(() => import("@/components/project/SessionPage").then(m => ({ default: m.SessionPage })));
const SimulationCurtain     = lazy(() => import("@/components/SimulationCurtain").then(m => ({ default: m.SimulationCurtain })));
const JurySimulationPage    = lazy(() => import("@/components/project/JurySimulationPage").then(m => ({ default: m.JurySimulationPage })));

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-xl border border-rule bg-bg-soft"
            />
          ))}
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

function Defense5Wrapper() {
  const [seen, setSeen] = useState(false);
  if (!seen) {
    return (
      <PageShell>
        <SimulationCurtain onComplete={() => setSeen(true)} />
      </PageShell>
    );
  }
  return (
    <PageShell>
      <JurySimulationPage />
    </PageShell>
  );
}

function GapHeatmapPage() {
  return (
    <PageShell>
      <GapHeatmapCard />
    </PageShell>
  );
}

export default function ProjectPage({
  params,
}: {
  params: Promise<{ id: string; slug?: string[] }>;
}) {
  const { id, slug } = use(params);
  const pageId = slug?.[0] ?? "overview";

  switch (pageId) {
    // ── Discovery ─────────────────────────────────────────────────────────
    case "discovery-1": return <PageShell><ResearchAreaConfirmPage /></PageShell>;
    case "discovery-2": return <PageShell><TopicSuggestionPage /></PageShell>;
    case "discovery-3": return <PageShell><BibliometricSummaryPage /></PageShell>;
    case "discovery-4": return <PageShell><ThematicAnalysisPage /></PageShell>;
    case "discovery-5": return <PageShell><ConceptNetworkPage /></PageShell>;

    // ── Curation ──────────────────────────────────────────────────────────
    case "curation-1": return <PageShell><AnchorRecommendationsPage /></PageShell>;
    case "curation-2": return <PageShell><ConnectedPapersPage /></PageShell>;
    case "curation-3": return <PageShell><MethodDataEthicsPage /></PageShell>;
    case "curation-4": return <PageShell><LiteratureSummaryPage /></PageShell>;
    case "curation-5": return <PageShell><ExtendedSummaryPage /></PageShell>;

    // ── GapAtlas ──────────────────────────────────────────────────────────
    case "gapatlas-1": return <GapHeatmapPage />;
    case "gapatlas-2": return <PageShell><GapProfilePage /></PageShell>;
    case "gapatlas-3": return <PageShell><OriginalityPage /></PageShell>;
    case "gapatlas-4": return <PageShell><GapComparisonPage /></PageShell>;
    case "gapatlas-5": return <PageShell><ImpactCurvePage /></PageShell>;

    // ── Authoring ─────────────────────────────────────────────────────────
    case "authoring-1": return <PageShell><PublicationTypePage /></PageShell>;
    case "authoring-2": return <PageShell><WritingSkeletonPage /></PageShell>;
    case "authoring-3": return <PageShell><AcademicLanguagePage /></PageShell>;
    case "authoring-4": return <PageShell><CitationQualityPage /></PageShell>;

    // ── Defense ───────────────────────────────────────────────────────────
    case "defense-1": return <PageShell><DefenseFormatPage /></PageShell>;
    case "defense-2": return <PageShell><ThesisContentPage /></PageShell>;
    case "defense-3": return <PageShell><IndividualFeedbackPage /></PageShell>;
    case "defense-4": return <PageShell><JournalSimulationPage /></PageShell>;
    case "defense-5": return <Defense5Wrapper />;
    case "defense-6": return <PageShell><ProjectClosurePage /></PageShell>;

    // ── Tools ─────────────────────────────────────────────────────────────
    case "notebook": return <PageShell><DiarySidebar projectId={id} /></PageShell>;
    case "session":  return <PageShell><SessionPage /></PageShell>;

    // ── Fallback ──────────────────────────────────────────────────────────
    default: {
      const title = pageId === "overview" ? "Proje Genel Bakis" : getPageTitle(pageId);
      const wb = findWorkbenchInfo(pageId);
      return (
        <PlaceholderPage
          title={title}
          workbenchLabel={wb.label || undefined}
          color={wb.color}
        />
      );
    }
  }
}
