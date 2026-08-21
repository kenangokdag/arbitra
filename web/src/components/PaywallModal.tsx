"use client";

import { Gavel, MessagesSquare, X, Check, Crown, Sparkles, type LucideIcon } from "lucide-react";
import { useNavigation } from "@/lib/navigation-context";

type FeatureInfo = {
  icon: LucideIcon;
  title: string;
  tagline: string;
  benefits: string[];
};

const FEATURES: Record<string, FeatureInfo> = {
  jury: {
    icon: Gavel,
    title: "Juri simulasyonu",
    tagline: "Tezinizi savunmadan once sanal juri ile prova yapin",
    benefits: [
      "Uc farkli bakis: yontem, literatur, bulgu hakemi",
      "Defense Readiness Score (DRS) ile hazirlik olcumu",
      "Her hakem icin detayli geri bildirim raporu",
      "Sinirsiz yeniden simulasyon, sinirsiz belge",
    ],
  },
  review: {
    icon: MessagesSquare,
    title: "Hakemlik simulasyonu",
    tagline: "Makaleniz dergiye gitmeden once hakem gozuyle okuyun",
    benefits: [
      "Bolum bolum detayli analiz (Method, Results, Discussion)",
      "Major/Minor Revision onerisi ve gerekcesi",
      "Her zayif yon icin \"Nasil duzeltilir?\" rehberi",
      "Editore mektup taslagi -- kopyala ve gonder",
    ],
  },
};

export function PaywallModal() {
  const { paywall, closePaywall } = useNavigation();
  if (!paywall.open) return null;

  const f = (FEATURES[paywall.feature ?? "jury"] ?? FEATURES.jury) as FeatureInfo;
  const Icon = f.icon;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: "rgba(15, 23, 42, 0.55)", backdropFilter: "blur(8px)", animation: "fadeIn 0.2s ease-out" }}
      onClick={closePaywall}
    >
      <div
        className="relative w-full max-w-md overflow-hidden rounded-3xl bg-white"
        style={{
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(217, 119, 6, 0.1)",
          animation: "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="h-1.5" style={{ background: "linear-gradient(90deg, #4F46E5, #7C3AED, #D97706)" }} />

        <button
          onClick={closePaywall}
          className="absolute right-4 top-4 z-10 flex h-8 w-8 items-center justify-center rounded-lg text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-700"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="p-8">
          <div className="mb-5 flex items-center gap-3">
            <div
              className="relative flex h-14 w-14 items-center justify-center rounded-2xl"
              style={{ background: "linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)" }}
            >
              <Icon className="h-6 w-6 text-amber-700" strokeWidth={2} />
              <div
                className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full text-white"
                style={{ background: "linear-gradient(135deg, #D97706 0%, #B45309 100%)" }}
              >
                <Crown className="h-2.5 w-2.5" strokeWidth={3} />
              </div>
            </div>
            <span
              className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold text-white"
              style={{ background: "linear-gradient(135deg, #D97706 0%, #B45309 100%)" }}
            >
              <Crown className="h-3 w-3" strokeWidth={2.5} />
              PRO
            </span>
          </div>

          <h2 className="font-display mb-2 text-2xl font-semibold italic leading-tight text-stone-900">{f.title}</h2>
          <p className="mb-6 text-sm leading-relaxed text-stone-600">{f.tagline}</p>

          <div className="mb-6 space-y-2.5 rounded-2xl bg-stone-50 p-4">
            {f.benefits.map((b, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 text-sm"
                style={{ animation: `fadeInUp 0.3s ease-out ${i * 80 + 100}ms both` }}
              >
                <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" strokeWidth={3} />
                <span className="leading-snug text-stone-800">{b}</span>
              </div>
            ))}
          </div>

          <div className="mb-5 flex items-center gap-2.5 rounded-xl border border-indigo-100 bg-indigo-50 p-3">
            <Sparkles className="h-4 w-4 flex-shrink-0 text-indigo-600" />
            <div className="flex-1 text-xs">
              <span className="font-semibold text-indigo-900">Demo deneme: </span>
              <span className="text-indigo-700">3 ucretsiz kullanim hakkiniz var (1/3 kullanildi)</span>
            </div>
          </div>

          <div className="space-y-2">
            <button
              className="flex w-full items-center justify-center gap-2 rounded-xl py-3.5 font-semibold text-white transition-all hover:scale-[1.01] active:scale-[0.99]"
              style={{
                background: "linear-gradient(135deg, #D97706 0%, #B45309 100%)",
                boxShadow: "0 4px 16px -4px rgba(217, 119, 6, 0.4)",
              }}
            >
              <Crown className="h-4 w-4" strokeWidth={2.5} />
              Pro'ya yukselt
            </button>
            <button onClick={closePaywall} className="w-full py-2 text-sm font-medium text-stone-600 transition-colors hover:text-stone-900">
              Demo ile devam et
            </button>
          </div>

          <p className="mt-4 text-center text-[11px] text-stone-400">
            Erken erisim fiyati henuz aciklanmadi - Listeye katilirsaniz size haber veririz
          </p>
        </div>
      </div>
    </div>
  );
}
