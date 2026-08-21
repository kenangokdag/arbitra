"use client";

import { useState } from "react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { Tags, Eye, EyeOff } from "lucide-react";

/* ---------- node & edge types ---------- */
interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  size: number; // diameter px
  cluster: number;
}

interface GraphEdge {
  source: string;
  target: string;
  lift: number;
  confidence: number;
}

/* ---------- 4 Tableau-10 cluster colors ---------- */
const CLUSTER_COLORS = ["#4C78A8", "#E45756", "#54A24B", "#F58518"];

/* ---------- 20 fixed nodes ---------- */
const NODES: GraphNode[] = [
  { id: "topsis",       label: "TOPSIS",           x: 280, y: 160, size: 55, cluster: 0 },
  { id: "ahp",          label: "AHP",              x: 200, y: 100, size: 60, cluster: 0 },
  { id: "mcdm",         label: "MCDM",             x: 320, y: 90,  size: 58, cluster: 0 },
  { id: "fuzzy",        label: "Fuzzy",            x: 160, y: 200, size: 50, cluster: 0 },
  { id: "vikor",        label: "VIKOR",            x: 360, y: 180, size: 42, cluster: 0 },
  { id: "electre",      label: "ELECTRE",          x: 250, y: 250, size: 38, cluster: 0 },
  { id: "promethee",    label: "PROMETHEE",        x: 140, y: 310, size: 36, cluster: 0 },
  { id: "bwm",          label: "BWM",              x: 90,  y: 140, size: 34, cluster: 0 },
  { id: "entropy",      label: "Entropy",          x: 420, y: 100, size: 40, cluster: 1 },
  { id: "critic",       label: "CRITIC",           x: 480, y: 170, size: 35, cluster: 1 },
  { id: "dea",          label: "DEA",              x: 520, y: 90,  size: 44, cluster: 1 },
  { id: "ml",           label: "Machine Learning", x: 580, y: 200, size: 48, cluster: 2 },
  { id: "regression",   label: "Regression",       x: 620, y: 280, size: 38, cluster: 2 },
  { id: "sem",          label: "SEM",              x: 540, y: 320, size: 36, cluster: 2 },
  { id: "factor",       label: "Factor Analysis",  x: 620, y: 360, size: 32, cluster: 2 },
  { id: "sustainability", label: "Sustainability", x: 380, y: 320, size: 46, cluster: 3 },
  { id: "esg",          label: "ESG",              x: 440, y: 380, size: 42, cluster: 3 },
  { id: "supply",       label: "Supply Chain",     x: 300, y: 370, size: 40, cluster: 3 },
  { id: "risk",         label: "Risk",             x: 460, y: 280, size: 44, cluster: 3 },
  { id: "education",    label: "Education",        x: 180, y: 380, size: 30, cluster: 3 },
];

/* ---------- edges ---------- */
const EDGES: GraphEdge[] = [
  { source: "topsis",  target: "ahp",       lift: 2.8, confidence: 0.72 },
  { source: "topsis",  target: "mcdm",      lift: 3.1, confidence: 0.85 },
  { source: "topsis",  target: "vikor",     lift: 2.5, confidence: 0.68 },
  { source: "topsis",  target: "fuzzy",     lift: 2.2, confidence: 0.61 },
  { source: "ahp",     target: "mcdm",      lift: 2.9, confidence: 0.80 },
  { source: "ahp",     target: "fuzzy",     lift: 2.4, confidence: 0.65 },
  { source: "ahp",     target: "bwm",       lift: 1.8, confidence: 0.45 },
  { source: "mcdm",    target: "entropy",   lift: 1.9, confidence: 0.52 },
  { source: "mcdm",    target: "vikor",     lift: 2.6, confidence: 0.70 },
  { source: "vikor",   target: "electre",   lift: 2.0, confidence: 0.55 },
  { source: "electre", target: "promethee", lift: 2.3, confidence: 0.62 },
  { source: "fuzzy",   target: "promethee", lift: 1.6, confidence: 0.40 },
  { source: "fuzzy",   target: "electre",   lift: 1.5, confidence: 0.38 },
  { source: "entropy", target: "critic",    lift: 2.7, confidence: 0.74 },
  { source: "entropy", target: "dea",       lift: 1.4, confidence: 0.35 },
  { source: "critic",  target: "dea",       lift: 1.7, confidence: 0.42 },
  { source: "dea",     target: "ml",        lift: 1.3, confidence: 0.30 },
  { source: "ml",      target: "regression", lift: 2.1, confidence: 0.58 },
  { source: "ml",      target: "sem",       lift: 1.5, confidence: 0.38 },
  { source: "regression", target: "factor", lift: 1.9, confidence: 0.50 },
  { source: "sem",     target: "factor",    lift: 2.0, confidence: 0.55 },
  { source: "sustainability", target: "esg", lift: 2.6, confidence: 0.71 },
  { source: "sustainability", target: "supply", lift: 2.0, confidence: 0.53 },
  { source: "sustainability", target: "risk", lift: 1.8, confidence: 0.46 },
  { source: "esg",     target: "risk",      lift: 2.2, confidence: 0.60 },
  { source: "supply",  target: "education", lift: 1.2, confidence: 0.28 },
  { source: "risk",    target: "ml",        lift: 1.6, confidence: 0.41 },
  { source: "mcdm",    target: "sustainability", lift: 1.7, confidence: 0.44 },
  { source: "topsis",  target: "supply",    lift: 1.5, confidence: 0.37 },
];

const CANVAS_W = 720;
const CANVAS_H = 440;

function getNodeById(id: string): GraphNode | undefined {
  return NODES.find((n) => n.id === id);
}

function getConnectedEdges(nodeId: string): GraphEdge[] {
  return EDGES.filter((e) => e.source === nodeId || e.target === nodeId);
}

function getConnectedNodeIds(nodeId: string): Set<string> {
  const set = new Set<string>();
  for (const e of EDGES) {
    if (e.source === nodeId) set.add(e.target);
    if (e.target === nodeId) set.add(e.source);
  }
  return set;
}

export function ConceptNetworkPage() {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string>("topsis");
  const [minLift, setMinLift] = useState(1.0);
  const [showLabels, setShowLabels] = useState(true);

  const filteredEdges = EDGES.filter((e) => e.lift >= minLift);
  const hoveredConnected = hoveredNode ? getConnectedNodeIds(hoveredNode) : null;

  const selectedNodeData = getNodeById(selectedNode);
  const selectedEdges = getConnectedEdges(selectedNode)
    .filter((e) => e.lift >= minLift)
    .sort((a, b) => b.lift - a.lift)
    .slice(0, 5);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Hangi yontem hangi konuyla yurur — sezgi degil, lift ve confidence ile soyluyorum." />

      <DataVizCard
        title="Kavram & Yontem Agi"
        badge="ARM N08 — lift & confidence"
        zoneTint="#E8A157"
      >
        <div className="flex gap-5">
          {/* ---- network canvas ---- */}
          <div className="flex-1">
            <div
              className="relative overflow-hidden rounded-xl border border-stone-100 bg-stone-50"
              style={{ width: "100%", height: CANVAS_H }}
            >
              {/* SVG edges */}
              <svg
                className="absolute inset-0"
                width="100%"
                height="100%"
                viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
                preserveAspectRatio="none"
              >
                {filteredEdges.map((edge, i) => {
                  const src = getNodeById(edge.source);
                  const tgt = getNodeById(edge.target);
                  if (!src || !tgt) return null;

                  const isHighlighted =
                    hoveredNode !== null &&
                    (edge.source === hoveredNode ||
                      edge.target === hoveredNode);
                  const isDimmed = hoveredNode !== null && !isHighlighted;

                  return (
                    <line
                      key={i}
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke={isHighlighted ? "#E8A157" : "#a8a29e"}
                      strokeWidth={
                        isHighlighted
                          ? Math.max(1.5, edge.lift)
                          : 0.5 + edge.lift * 0.5
                      }
                      strokeOpacity={isDimmed ? 0.1 : isHighlighted ? 0.9 : 0.25}
                    />
                  );
                })}
              </svg>

              {/* nodes */}
              {NODES.map((node) => {
                const isDimmed =
                  hoveredNode !== null &&
                  hoveredNode !== node.id &&
                  hoveredConnected !== null &&
                  !hoveredConnected.has(node.id);
                const isHov = hoveredNode === node.id;

                return (
                  <div
                    key={node.id}
                    className="absolute flex cursor-pointer items-center justify-center rounded-full border-2 transition-all"
                    style={{
                      left: `${(node.x / CANVAS_W) * 100}%`,
                      top: `${(node.y / CANVAS_H) * 100}%`,
                      width: node.size,
                      height: node.size,
                      transform: "translate(-50%, -50%)",
                      background: CLUSTER_COLORS[node.cluster],
                      borderColor: isHov ? "#E8A157" : "white",
                      opacity: isDimmed ? 0.2 : 1,
                      zIndex: isHov ? 20 : 10,
                      boxShadow: isHov
                        ? "0 0 0 3px rgba(232,161,87,0.3)"
                        : "0 1px 2px rgba(0,0,0,0.1)",
                    }}
                    onMouseEnter={() => setHoveredNode(node.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={() => setSelectedNode(node.id)}
                  >
                    {showLabels && (
                      <span
                        className="pointer-events-none absolute whitespace-nowrap text-[10px] font-semibold"
                        style={{
                          top: `${node.size / 2 + 6}px`,
                          color: CLUSTER_COLORS[node.cluster],
                          opacity: isDimmed ? 0.3 : 1,
                        }}
                      >
                        {node.label}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* controls */}
            <div className="mt-4 flex items-center gap-6">
              <label className="flex items-center gap-2 text-[13px] text-stone-600">
                Min lift esigi:
                <input
                  type="range"
                  min={1.0}
                  max={3.0}
                  step={0.1}
                  value={minLift}
                  onChange={(e) => setMinLift(Number(e.target.value))}
                  className="h-1.5 w-28 cursor-pointer accent-amber-500"
                />
                <span className="w-8 text-right text-[12px] text-stone-400">
                  {minLift.toFixed(1)}
                </span>
              </label>

              <label className="flex items-center gap-2 text-[13px] text-stone-600">
                <input
                  type="checkbox"
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                  className="h-4 w-4 rounded border-stone-300 accent-amber-500"
                />
                {showLabels ? (
                  <Eye className="h-3.5 w-3.5 text-stone-500" />
                ) : (
                  <EyeOff className="h-3.5 w-3.5 text-stone-400" />
                )}
                Etiketleri goster
              </label>

              <label className="flex items-center gap-2 text-[13px] text-stone-600">
                <Tags className="h-3.5 w-3.5 text-stone-500" />
                <select className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-[13px] text-stone-700 outline-none focus:border-amber-300">
                  <option>Tum kumeler</option>
                  <option>MCDM Yontemleri</option>
                  <option>Agirlik Yontemleri</option>
                  <option>Istatistik</option>
                  <option>Uygulama Alanlari</option>
                </select>
              </label>
            </div>
          </div>

          {/* ---- right panel: selected node detail ---- */}
          <div className="w-[280px] flex-shrink-0">
            <div
              className="rounded-2xl border border-stone-200 bg-white p-4"
              style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
            >
              {selectedNodeData && (
                <>
                  <div className="mb-4 flex items-center gap-3">
                    <span
                      className="flex h-10 w-10 items-center justify-center rounded-full text-[11px] font-bold text-white"
                      style={{
                        background:
                          CLUSTER_COLORS[selectedNodeData.cluster],
                      }}
                    >
                      {selectedNodeData.label.slice(0, 2)}
                    </span>
                    <div>
                      <h4 className="font-display text-sm font-semibold text-stone-900">
                        {selectedNodeData.label}
                      </h4>
                      <span className="text-[11px] text-stone-400">
                        Frekans: {selectedNodeData.size * 47}
                      </span>
                    </div>
                  </div>

                  <h5 className="mb-2 text-[12px] font-semibold uppercase tracking-wider text-stone-400">
                    Bagli terimler (Top 5)
                  </h5>
                  <div className="space-y-2">
                    {selectedEdges.map((edge, i) => {
                      const otherId =
                        edge.source === selectedNode
                          ? edge.target
                          : edge.source;
                      const other = getNodeById(otherId);
                      if (!other) return null;
                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between rounded-lg border border-stone-100 px-3 py-2"
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{
                                background:
                                  CLUSTER_COLORS[other.cluster],
                              }}
                            />
                            <span className="text-[13px] font-medium text-stone-700">
                              {other.label}
                            </span>
                          </div>
                          <div className="text-right">
                            <span className="block text-[11px] font-semibold text-stone-600">
                              lift {edge.lift.toFixed(1)}
                            </span>
                            <span className="block text-[10px] text-stone-400">
                              conf {(edge.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                    {selectedEdges.length === 0 && (
                      <p className="text-[12px] italic text-stone-400">
                        Lift esiginde baglanti yok.
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </DataVizCard>
    </div>
  );
}
