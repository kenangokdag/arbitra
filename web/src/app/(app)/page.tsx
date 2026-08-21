"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Search, BookOpen, MessageSquare, Sparkles } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card, CardRow } from "@/components/Card";
import { PaperCard } from "@/components/PaperCard";
import { Hint } from "@/components/Hint";
import { apiFetch } from "@/lib/api";
import type { Top5Response, ReadingListResponse } from "@/lib/types";

const QUICK_TOPICS = [
  "multi-criteria decision making",
  "higher education accreditation",
  "AHP TOPSIS hybrid approach",
  "educational quality assessment",
] as const;

export default function HomePage() {
  // SSR-safe stable initial; client mount sonrası rastgele seçim — hydration mismatch'i önlemek için
  const [topic, setTopic] = useState<string>(QUICK_TOPICS[0]);
  useEffect(() => {
    const next = QUICK_TOPICS[Math.floor(Math.random() * QUICK_TOPICS.length)];
    if (next) setTopic(next);
  }, []);

  const top5 = useQuery<Top5Response>({
    queryKey: ["top5", "home", topic],
    queryFn: () =>
      apiFetch<Top5Response>("/api/top5", {
        method: "POST",
        body: { query: topic, session_id: "home", k: 3 },
      }),
  });

  const readingList = useQuery<ReadingListResponse>({
    queryKey: ["reading-list"],
    queryFn: () => apiFetch<ReadingListResponse>("/api/reading-list"),
  });

  const rlCount = readingList.data?.count ?? 0;
  const papers = top5.data?.papers ?? [];
  const isNewUser = rlCount === 0 && !top5.isLoading;

  if (isNewUser && papers.length === 0) {
    return (
      <>
        <PageHeader
          title="Arbitra'ya hoş geldiniz"
          lede="Akademik literatür tarama asistanınız hazır. Başlamak için aşağıdaki adımlardan birini seçin."
        />

        {top5.isError && (
          <Hint>Backend bağlantısı kurulamadı — veriler yüklenemedi.</Hint>
        )}

        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Link
            href="/search"
            className="group flex flex-col items-center gap-3 rounded-xl border border-rule bg-bg-card p-6 text-center transition-all duration-200 hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
          >
            <Search className="h-8 w-8 text-accent transition-transform duration-200 group-hover:scale-110" />
            <h3 className="text-[15px] font-medium text-ink">Makale Ara</h3>
            <p className="text-[13px] text-ink-mute">
              Anahtar kelime veya cümle ile arayın, en kaliteli sonuçları görün.
            </p>
          </Link>
          <Link
            href="/chat"
            className="group flex flex-col items-center gap-3 rounded-xl border border-rule bg-bg-card p-6 text-center transition-all duration-200 hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
          >
            <MessageSquare className="h-8 w-8 text-accent transition-transform duration-200 group-hover:scale-110" />
            <h3 className="text-[15px] font-medium text-ink">Sohbet</h3>
            <p className="text-[13px] text-ink-mute">
              Makaleler hakkında sorular sorun, kaynak alıntılı cevaplar alın.
            </p>
          </Link>
          <Link
            href="/onboarding"
            className="group flex flex-col items-center gap-3 rounded-xl border border-rule bg-bg-card p-6 text-center transition-all duration-200 hover:-translate-y-0.5 hover:border-accent hover:shadow-md"
          >
            <Sparkles className="h-8 w-8 text-accent transition-transform duration-200 group-hover:scale-110" />
            <h3 className="text-[15px] font-medium text-ink">Profilimi Ayarla</h3>
            <p className="text-[13px] text-ink-mute">
              Araştırma alanınızı belirleyin, kişiselleştirilmiş öneriler alın.
            </p>
          </Link>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Hoş geldiniz"
        lede="Bugün ne yapmak istersiniz? Aşağıda önerileriniz ve okuma listeniz var."
      />

      {top5.isError && (
        <Hint>Backend bağlantısı kurulamadı — veriler yüklenemedi.</Hint>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { n: rlCount, l: "okuma listenizde", c: "border-l-accent" },
          { n: papers.length, l: "önerilen makale", c: "border-l-info" },
        ].map((s) => (
          <div
            key={s.l}
            className={`rounded-[10px] border border-rule border-l-4 ${s.c} bg-bg-card px-5 py-4 transition-shadow duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:shadow-sm`}
          >
            <div className="serif text-[28px] font-medium leading-none tracking-[-0.01em]">
              {s.n}
            </div>
            <div className="mt-1.5 text-[12.5px] text-ink-mute">{s.l}</div>
          </div>
        ))}
      </div>

      {/* Konu seçimi */}
      <div className="mb-4 flex flex-wrap items-center gap-1.5 text-[12.5px]">
        <span className="text-ink-mute">Öneri konusu:</span>
        {QUICK_TOPICS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTopic(t)}
            className={`rounded-full border px-2.5 py-1 transition-colors duration-150 ${
              topic === t
                ? "border-accent bg-accent/10 text-accent"
                : "border-rule bg-bg-card text-ink-mute hover:bg-bg-hover"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {top5.isLoading && (
        <div className="mb-6 flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl border border-rule bg-bg-soft" />
          ))}
        </div>
      )}

      {papers.length > 0 && (
        <section className="mb-6">
          <h2 className="serif mb-3 text-[16px] font-medium italic text-ink-soft">
            Önerilen makaleler
          </h2>
          <div className="flex flex-col gap-4">
            {papers.map((paper) => (
              <PaperCard key={paper.paper_id} paper={paper} compact />
            ))}
          </div>
        </section>
      )}

      <CardRow>
        <Card title="Yeni arama" className="border-accent-soft bg-accent-pale">
          <p className="text-[13.5px] leading-relaxed text-ink-soft">
            Farklı bir konuda makale arayın — sistem ilk 50 sonucu kanıt
            kalitesine göre sıralayıp size en uygun olanları öne çıkarsın.
          </p>
          <Link
            href="/search"
            className="mt-2 inline-block text-[13px] font-medium text-accent hover:underline"
          >
            Makale ara →
          </Link>
        </Card>
        <Card title="Okuma listem" className="border-info/20 bg-info-pale">
          <p className="text-[13.5px] leading-relaxed text-ink-soft">
            {rlCount > 0
              ? `Listenizde ${rlCount} makale var.`
              : "Listeniz boş — arama sonuçlarından makale ekleyin."}
          </p>
          <Link
            href="/reading-list"
            className="mt-2 inline-block text-[13px] font-medium text-accent hover:underline"
          >
            Listeye git →
          </Link>
        </Card>
      </CardRow>
    </>
  );
}
