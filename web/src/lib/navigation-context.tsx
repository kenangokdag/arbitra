"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api";
import { BRAND } from "./brand";
import { buildBreadcrumb, workbenches } from "./nav-config";
import type { ProjectListItem } from "./types";

type PaywallState = { open: boolean; feature: string | null };

// V1-S14 P003: live `/api/project` listesinden türeyen UI projeksiyonu.
// Backend `ProjectListItem` (id, name, status, current_stage, updated_at) +
// UI extras (color palette, paperCount placeholder). MOCK_PROJECTS söküldü.
export type Project = {
  id: string;
  name: string;
  status: ProjectListItem["status"];
  currentStage: string;
  updatedAt: string;
  color: string;
  paperCount: number;
};

const PROJECT_COLOR_PALETTE = [
  "#4F46E5",
  "#7C3AED",
  "#D97706",
  "#0E7490",
  "#16A34A",
  "#DB2777",
] as const;

function pickProjectColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) | 0;
  }
  const idx = Math.abs(hash) % PROJECT_COLOR_PALETTE.length;
  return PROJECT_COLOR_PALETTE[idx]!;
}

function mapProject(item: ProjectListItem): Project {
  return {
    id: item.id,
    name: item.name,
    status: item.status,
    currentStage: item.current_stage,
    updatedAt: item.updated_at,
    color: pickProjectColor(item.id),
    paperCount: 0,
  };
}

type NavigationContextValue = {
  // Sidebar
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
  mobileOpen: boolean;
  setMobileOpen: (v: boolean) => void;
  openWorkbench: string | null;
  setOpenWorkbench: (v: string | null) => void;

  // Project
  projects: Project[];
  projectsLoading: boolean;
  activeProjectId: string | null;
  activeProject: Project | null;
  inProject: boolean;
  enterProject: (projectId: string) => void;
  exitProject: () => void;

  // Navigation
  currentPageId: string;
  navigateTo: (pageId: string) => void;
  breadcrumb: string[];

  // Paywall
  paywall: PaywallState;
  openPaywall: (feature: string) => void;
  closePaywall: () => void;
};

const NavigationContext = createContext<NavigationContextValue | null>(null);

export function useNavigation() {
  const ctx = useContext(NavigationContext);
  if (!ctx) throw new Error("useNavigation must be used within NavigationProvider");
  return ctx;
}

/** Derive current page ID from Next.js pathname */
function derivePageId(pathname: string): string {
  // /project/p1/discovery-3 → discovery-3
  const projectMatch = pathname.match(/^\/project\/[^/]+\/(.+)$/);
  if (projectMatch) return projectMatch[1] ?? "";

  // /project/p1 → overview
  if (/^\/project\/[^/]+\/?$/.test(pathname)) return "overview";

  // / → dashboard
  if (pathname === "/") return "dashboard";

  // /q → vitrin pageId
  if (pathname === "/q" || pathname === "/q/") return "q";

  // /review → hakemlik tool pageId (flat route, proje-dışı)
  if (pathname === "/review" || pathname.startsWith("/review/")) return "review";

  // /search, /chat etc → keep as flat route (not a pageId)
  return "";
}

/** Derive project ID from pathname */
function deriveProjectId(pathname: string): string | null {
  const m = pathname.match(/^\/project\/([^/]+)/);
  return m?.[1] ?? null;
}

export function NavigationProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // openWorkbench = path-bazlı auto + manuel override.
  // Override sadece kendi path'inde geçerli; path değişince auto'ya dönülür.
  const [userOverride, setUserOverride] = useState<
    { path: string; wb: string | null } | null
  >(null);
  const [paywall, setPaywall] = useState<PaywallState>({ open: false, feature: null });

  // V1-S14 P003 — `GET /api/project` canlı sorgu. Empty state: projects=[],
  // activeProject=null. Sidebar in-project bloku activeProject null olunca
  // render edilmez.
  const projectsQuery = useQuery<ProjectListItem[]>({
    queryKey: ["projects", "list"],
    queryFn: () => apiFetch<ProjectListItem[]>("/api/project"),
  });
  const projects: Project[] = (projectsQuery.data ?? []).map(mapProject);
  const projectsLoading = projectsQuery.isLoading;

  // Derive state from URL
  const urlProjectId = deriveProjectId(pathname);
  const inProject = urlProjectId !== null;
  const activeProjectId = urlProjectId;
  const activeProject =
    activeProjectId !== null
      ? projects.find((p) => p.id === activeProjectId) ?? null
      : null;
  const currentPageId = derivePageId(pathname);

  const autoWorkbenchId =
    workbenches.find((w) => w.pages.some((p) => p.id === currentPageId))?.id ??
    null;

  const openWorkbench =
    userOverride && userOverride.path === pathname
      ? userOverride.wb
      : autoWorkbenchId;

  const setOpenWorkbench = useCallback(
    (wb: string | null) => {
      setUserOverride({ path: pathname, wb });
    },
    [pathname],
  );

  const breadcrumb = inProject
    ? buildBreadcrumb(currentPageId, activeProject?.name ?? "")
    : currentPageId === "dashboard" || currentPageId === ""
      ? buildBreadcrumb("dashboard", "")
      : [BRAND];

  const enterProject = useCallback(
    (projectId: string) => {
      // F10-F6: Q (vitrin/OpenAlex) → Atelye (proje/bizim havuz) gecisi.
      // Discovery-1 = arastirma alani onay sayfasi (Kutuphaneci sohbeti +
      // capa kilidi). discovery-1 → discovery-2 (konu) → discovery-3 (bibliyometrik).
      // Onceki: dogrudan discovery-3'e atliyordu — Q ile proje arasi semantik
      // kopukluk nedeniyle yanlisti (Q OpenAlex, proje warehouse).
      setOpenWorkbench("discovery");
      router.push(`/project/${projectId}/discovery-1`);
    },
    [router, setOpenWorkbench],
  );

  const exitProject = useCallback(() => {
    router.push("/");
  }, [router]);

  const navigateTo = useCallback(
    (pageId: string) => {
      if (pageId === "dashboard") {
        router.push("/");
        return;
      }
      // Vitrin tek sayfa flat URL (/q)
      if (pageId === "q") {
        router.push("/q");
        setMobileOpen(false);
        return;
      }
      // Hakemlik flat URL (/review) — proje-dışı, tek başına araç
      if (pageId === "review") {
        router.push("/review");
        setMobileOpen(false);
        return;
      }
      if (inProject && activeProjectId) {
        router.push(`/project/${activeProjectId}/${pageId}`);
        setMobileOpen(false);
        return;
      }
      // Out of project (or no active project) → kullanıcı önce proje
      // oluşturmalı. Onboarding/Q üzerinden Project oluşturma ile başlar.
      router.push("/onboarding");
      setMobileOpen(false);
    },
    [router, inProject, activeProjectId],
  );

  const openPaywall = useCallback((feature: string) => {
    setPaywall({ open: true, feature });
  }, []);

  const closePaywall = useCallback(() => {
    setPaywall({ open: false, feature: null });
  }, []);

  return (
    <NavigationContext.Provider
      value={{
        collapsed,
        setCollapsed,
        mobileOpen,
        setMobileOpen,
        openWorkbench,
        setOpenWorkbench,
        projects,
        projectsLoading,
        activeProjectId,
        activeProject,
        inProject,
        enterProject,
        exitProject,
        currentPageId,
        navigateTo,
        breadcrumb,
        paywall,
        openPaywall,
        closePaywall,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
}
