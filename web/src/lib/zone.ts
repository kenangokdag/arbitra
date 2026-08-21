/**
 * B42-051 — 4-Zone Design System
 *
 * Her tezgâh kendi atmosferine sahip. Zone aktif olduğunda
 * CSS variable'lar otomatik override olur (globals.css [data-zone]).
 *
 * Kullanım:
 *   <main data-zone={getZone("discovery-3")}>
 *     ...sayfa içeriği...
 *   </main>
 */

export type Zone =
  | "discovery"
  | "curation"
  | "gapatlas"
  | "authoring"
  | "defense";

/** Route prefix → zone mapping */
const ZONE_MAP: Record<string, Zone> = {
  discovery: "discovery",
  curation: "curation",
  gapatlas: "gapatlas",
  authoring: "authoring",
  defense: "defense",
};

/** Sayfa ID'sinden zone çıkar (sidebar page ID formatı: "discovery-3") */
export function getZone(pageId: string): Zone | undefined {
  const prefix = pageId.split("-")[0];
  return prefix ? ZONE_MAP[prefix] : undefined;
}

/** Zone → accent renk (JS tarafında ihtiyaç olursa, chart vb.) */
export const ZONE_ACCENT: Record<Zone, string> = {
  discovery: "#E8A157",
  curation: "#E8A157",
  gapatlas: "#0E4F4A",
  authoring: "#E8A157",
  defense: "#C9A961",
};

/** Zone → Türkçe label */
export const ZONE_LABEL: Record<Zone, string> = {
  discovery: "Keşif",
  curation: "Süzme & İnceleme",
  gapatlas: "Literatür Boşluğu",
  authoring: "Yazım & Hazırlık",
  defense: "Savunma",
};

/** Danışman amber — tüm zone'larda sabit */
export const ADVISOR_AMBER = "#E8A157";
