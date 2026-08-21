"use client";

import { useState } from "react";
import { Check, X, Loader2, Sparkles } from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch } from "@/lib/api";

interface Suggestion {
  original: string;
  suggested: string;
  type: "Akademik ton" | "Netlik" | "Referans dili";
}

interface ChatChunk { delta: string; finished: boolean; citation_paper_ids: string[]; }

const LANG_SYSTEM =
  "Sen bir akademik dil editörüsün. Kullanıcının verdiği Türkçe akademik metni analiz et. " +
  "Dil, ton ve netlik sorunlarını bul. " +
  "Yanıtını SADECE şu JSON formatında ver — açıklama veya markdown ekleme: " +
  '[{"original":"...","suggested":"...","type":"Akademik ton|Netlik|Referans dili"},...]';

const typeBadgeColor: Record<Suggestion["type"], string> = {
  "Akademik ton": "bg-blue-50 text-blue-600",
  Netlik: "bg-emerald-50 text-emerald-600",
  "Referans dili": "bg-purple-50 text-purple-600",
};

function parseSuggestions(delta: string): Suggestion[] | null {
  const jsonMatch = delta.match(/\[[\s\S]*\]/);
  if (!jsonMatch) return null;
  try {
    const parsed = JSON.parse(jsonMatch[0]) as unknown[];
    if (!Array.isArray(parsed)) return null;
    return parsed.filter(
      (item): item is Suggestion =>
        typeof item === "object" &&
        item !== null &&
        "original" in item &&
        "suggested" in item &&
        "type" in item
    );
  } catch {
    return null;
  }
}

export function AcademicLanguagePage() {
  const [inputText, setInputText] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [rawAnalysis, setRawAnalysis] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState<Set<number>>(new Set());
  const [rejected, setRejected] = useState<Set<number>>(new Set());

  const analyze = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);
    setSuggestions(null);
    setRawAnalysis(null);
    setAccepted(new Set());
    setRejected(new Set());
    try {
      const resp = await apiFetch<ChatChunk>("/api/chat", {
        method: "POST",
        body: {
          session_id: "lang-analysis",
          messages: [
            { role: "system", content: LANG_SYSTEM },
            { role: "user", content: inputText.slice(0, 4000) },
          ],
          language: "tr",
        },
      });
      const parsed = parseSuggestions(resp.delta);
      if (parsed && parsed.length > 0) {
        setSuggestions(parsed);
      } else {
        setRawAnalysis(resp.delta);
      }
    } catch {
      setError("Analiz yapılamadı. Backend bağlantısını kontrol edin.");
    } finally {
      setLoading(false);
    }
  };

  const acceptAll = () => {
    if (!suggestions) return;
    setAccepted(new Set(suggestions.map((_, i) => i)));
  };

  const displaySuggestions = suggestions ?? [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Yazim dilini birlikte gozden gecirelim — konu ve yontem context'iyle, sadece dilbilgisi degil." />

      {/* Text input */}
      <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-display mb-3 text-sm font-semibold text-stone-700">
          Analiz edilecek metin
        </h3>
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Akademik metninizi buraya yapıştırın (paragraf, bölüm veya özet)..."
          rows={6}
          className="w-full rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-700 outline-none focus:border-amber-300 focus:ring-2 focus:ring-amber-100"
        />
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={analyze}
            disabled={!inputText.trim() || loading}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#E8A157] to-amber-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Dil Analizi Yap
          </button>
          <span className="text-xs text-stone-400">{inputText.length} / 4000 karakter</span>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-3 rounded-2xl border border-stone-100 bg-stone-50 p-6 text-stone-400">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm">Akademik dil analizi yapılıyor...</span>
        </div>
      )}

      {/* Raw analysis fallback */}
      {rawAnalysis && (
        <div className="rounded-2xl border border-amber-100 bg-amber-50 p-5">
          <h3 className="font-display mb-3 text-sm font-semibold text-amber-800">Danışman Analizi</h3>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-stone-700">{rawAnalysis}</p>
        </div>
      )}

      {/* Structured suggestions */}
      {displaySuggestions.length > 0 && (
        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Suggestion list */}
          <div className="w-full lg:w-[340px]">
            <div className="space-y-3">
              {displaySuggestions.map((s, idx) => {
                const isAccepted = accepted.has(idx);
                const isRejected = rejected.has(idx);
                return (
                  <div
                    key={idx}
                    className={`rounded-2xl border p-4 transition-opacity ${
                      isRejected ? "opacity-40" : ""
                    } ${isAccepted ? "border-emerald-200 bg-emerald-50/40" : "border-stone-200 bg-white"}`}
                  >
                    <span
                      className={`mb-2 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${typeBadgeColor[s.type] ?? "bg-stone-100 text-stone-600"}`}
                    >
                      {s.type}
                    </span>
                    <p className="text-sm text-stone-400 line-through">{s.original}</p>
                    <p className="mt-1.5 rounded-lg bg-emerald-50/60 p-2 text-sm text-stone-700">
                      {s.suggested}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => setAccepted((prev) => { const s2 = new Set(prev); s2.has(idx) ? s2.delete(idx) : s2.add(idx); return s2; })}
                        className={`flex flex-1 items-center justify-center gap-1 rounded-lg border py-1.5 text-xs font-medium transition-colors ${
                          isAccepted
                            ? "border-emerald-400 bg-emerald-100 text-emerald-700"
                            : "border-emerald-200 text-emerald-600 hover:bg-emerald-50"
                        }`}
                      >
                        <Check className="h-3.5 w-3.5" />
                        {isAccepted ? "Kabul edildi" : "Kabul et"}
                      </button>
                      <button
                        onClick={() => setRejected((prev) => { const s2 = new Set(prev); s2.has(idx) ? s2.delete(idx) : s2.add(idx); return s2; })}
                        className={`flex flex-1 items-center justify-center gap-1 rounded-lg border py-1.5 text-xs font-medium transition-colors ${
                          isRejected
                            ? "border-stone-400 bg-stone-100 text-stone-600"
                            : "border-stone-200 text-stone-400 hover:bg-stone-50"
                        }`}
                      >
                        <X className="h-3.5 w-3.5" />
                        Reddet
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Revised text panel */}
          <div className="flex-1">
            <div className="min-h-[400px] rounded-2xl border border-stone-200 bg-white p-6">
              <h3 className="font-display mb-4 text-sm font-semibold text-stone-700">
                Revize Edilmiş Metin
              </h3>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-stone-700">
                {(() => {
                  let result = inputText;
                  accepted.forEach((i) => {
                    const sg = displaySuggestions[i];
                    if (sg) result = result.replace(sg.original, sg.suggested);
                  });
                  return result || inputText;
                })()}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Bottom buttons */}
      {displaySuggestions.length > 0 && (
        <div className="flex gap-3">
          <button
            onClick={acceptAll}
            className="rounded-xl bg-gradient-to-r from-[#E8A157] to-amber-500 px-6 py-2.5 text-sm font-medium text-white shadow-sm transition-shadow hover:shadow"
          >
            Tüm önerileri kabul et
          </button>
          <button
            onClick={analyze}
            disabled={loading}
            className="rounded-xl border border-stone-200 bg-white px-6 py-2.5 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-50"
          >
            Yeniden Analiz Et
          </button>
        </div>
      )}
    </div>
  );
}
