import {
  Compass,
  Library,
  Map,
  PenTool,
  Shield,
  Globe,
  BookOpen,
  MessagesSquare,
  User,
  Sparkles,
  Gavel,
  type LucideIcon,
} from "lucide-react";
import { BRAND } from "@/lib/brand";

export type PageStatus = "completed" | "current" | "locked" | "available";

export type WorkbenchPage = {
  id: string;
  label: string;
  status?: PageStatus;
  lockedReason?: string;
};

export type Workbench = {
  id: string;
  label: string;
  icon: LucideIcon;
  color: string;
  pages: WorkbenchPage[];
};

export type GeneralItem = {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
};

export type ToolItem = {
  id: string;
  label: string;
  icon: LucideIcon;
};

export const workbenches: Workbench[] = [
  {
    id: "vitrin",
    label: "Vitrin",
    icon: Sparkles,
    color: "#0e7490",
    pages: [
      { id: "q", label: "Hizli Inceleme" },
    ],
  },
  {
    id: "discovery",
    label: "Kesif",
    icon: Compass,
    color: "#4F46E5",
    pages: [
      { id: "discovery-1", label: "Arastirma Alani" },
      { id: "discovery-2", label: "Konu Belirleme" },
      { id: "discovery-3", label: "Bibliyometrik Analiz" },
      { id: "discovery-4", label: "Tematik Analiz" },
      { id: "discovery-5", label: "Kavram Agi" },
    ],
  },
  {
    id: "curation",
    label: "Inceleme",
    icon: Library,
    color: "#4F46E5",
    pages: [
      { id: "curation-1", label: "Onerilen Literatur" },
      { id: "curation-2", label: "Iliskili Calismalar" },
      { id: "curation-3", label: "Yontem & Veri Kalitesi" },
      { id: "curation-4", label: "Literatur Sentezi" },
      { id: "curation-5", label: "Genisletilmis Sentez" },
    ],
  },
  {
    id: "gapatlas",
    label: "Literatur Boslugu",
    icon: Map,
    color: "#0E4F4A",
    pages: [
      { id: "gapatlas-1", label: "Bosluk Haritasi" },
      { id: "gapatlas-2", label: "Bosluk Profili" },
      { id: "gapatlas-3", label: "Ozgunluk Degerlendirmesi" },
      { id: "gapatlas-4", label: "Calisma Karsilastirmasi" },
      { id: "gapatlas-5", label: "Akademik Etki Egrisi" },
    ],
  },
  {
    id: "authoring",
    label: "Yazim & Hazirlik",
    icon: PenTool,
    color: "#4F46E5",
    pages: [
      { id: "authoring-1", label: "Yayin Formati" },
      { id: "authoring-2", label: "Makale Taslagi" },
      { id: "authoring-3", label: "Akademik Dil & Uslup" },
      { id: "authoring-4", label: "Atif & Stil Kilavuzu" },
    ],
  },
  {
    id: "defense",
    label: "Savunma",
    icon: Shield,
    color: "#C9A961",
    pages: [
      { id: "defense-1", label: "Savunma Formati" },
      { id: "defense-2", label: "Tez Icerik Analizi" },
      { id: "defense-3", label: "Bireysel Geri Bildirim" },
      { id: "defense-4", label: "Dergi Simulasyonu" },
      { id: "defense-5", label: "Juri Simulasyonu" },
      { id: "defense-6", label: "Proje Tamamlama" },
    ],
  },
];

export const toolItems: ToolItem[] = [
  { id: "review", label: BRAND, icon: Gavel },
  { id: "explore", label: "Hizli Tarama", icon: Globe },
  { id: "notebook", label: "Arastirma Defteri", icon: BookOpen },
  { id: "session", label: "Calisma Oturumu", icon: MessagesSquare },
];

export const generalItems: GeneralItem[] = [
  { id: "library", label: "Kutuphanem", icon: Library, href: "/reading-list" },
  { id: "profile", label: "Profilim", icon: User, href: "/onboarding" },
];

/** Build breadcrumb array from a project page ID + project name */
export function buildBreadcrumb(pageId: string, projectName: string): string[] {
  // Dashboard
  if (pageId === "dashboard" || pageId === "") return ["Panelim"];
  if (pageId === "overview") return ["Projelerim", projectName, "Genel bakis"];

  // Workbench pages
  for (const wb of workbenches) {
    const page = wb.pages.find((p) => p.id === pageId);
    if (page) return ["Projelerim", projectName, wb.label, page.label];
  }

  // Tool pages
  const tool = toolItems.find((t) => t.id === pageId);
  if (tool) return ["Projelerim", projectName, tool.label];

  // Fallback
  return [BRAND];
}

/** Get page title from ID */
export function getPageTitle(pageId: string): string {
  for (const wb of workbenches) {
    const page = wb.pages.find((p) => p.id === pageId);
    if (page) return page.label;
  }
  const tool = toolItems.find((t) => t.id === pageId);
  if (tool) return tool.label;
  return pageId;
}

/** Get workbench info for a page ID */
export function findWorkbenchInfo(pageId: string): { label: string; color: string } {
  const prefix = pageId.split("-")[0];
  const wb = workbenches.find((w) => w.id === prefix);
  if (wb) return { label: wb.label, color: wb.color };
  return { label: "", color: "#94A3B8" };
}
