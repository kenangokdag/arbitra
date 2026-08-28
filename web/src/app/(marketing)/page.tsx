"use client";

/* ============================================================
   ARBITRA Landing — saf hakemlik (peer-review prova) tanıtımı
   ------------------------------------------------------------
   Kilitli yön: web/DESIGN-DECISIONS-LANDING.md (anti-toolbox §1-8).
   RUH: dergiye göndermeden önce, üç bağımsız hakemin önüne çık —
   yargıyı, kanıtı ve düzeltmeyi şimdi gör. Sakin, otoriter, dürüst.

   İMZA ANI (hero): yakınsayan jüri (yöntemci/şüpheci/yapıcı) →
   tek verdict + tıklanabilir kanıt-çıpası (cümle → neden → fix).
   Tüm demo verisi "örnek değerlendirme" etiketli; uydurma metrik YOK.

   Marka: ArbitraWordmark + BRAND/tagline. Tek aksan = var(--color-accent).
   Eski turuncu aksan ve gap-analiz omurgası emekli.
   ============================================================ */

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  X,
  Quote,
  Lock,
  Eye,
  AlertCircle,
  FileText,
  Trash2,
  Shield,
} from "lucide-react";
import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";
import { BRAND, BRAND_TAGLINE_TR } from "@/lib/brand";
import { SplashOverlay } from "./SplashOverlay";
import { WaitlistModal } from "@/components/marketing/WaitlistModal";
import type { WaitlistSource } from "@/lib/waitlist-api";

/* Tek aksan token'ı — renk değeri brand canon'da (globals @theme). */
const ACCENT = "var(--color-accent)";

/* "örnek değerlendirme" rozeti — her demo yüzeyinde tekrar eder (dürüstlük). */
function SampleTag({ onDark = false }: { onDark?: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-sans text-[10.5px] font-medium uppercase tracking-[0.1em]"
      style={{
        color: onDark
          ? "color-mix(in oklab, var(--color-bg) 70%, transparent)"
          : "var(--color-ink-faint)",
        borderColor: onDark
          ? "color-mix(in oklab, var(--color-bg) 24%, transparent)"
          : "var(--color-rule)",
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: ACCENT }}
      />
      Örnek değerlendirme
    </span>
  );
}

/* ============================================================
   NAV
   ============================================================ */
function Nav({ onWaitlist }: { onWaitlist: () => void }) {
  const links = [
    ["Nasıl çalışır", "#nasil-calisir"],
    ["Panel", "#panel"],
    ["Dürüstlük", "#durustluk"],
    ["Gizlilik", "#gizlilik"],
    ["Karşılaştırma", "#karsilastirma"],
  ];
  return (
    <nav
      className="sticky top-0 z-50 border-b backdrop-blur"
      style={{
        background: "color-mix(in oklab, var(--color-bg) 92%, transparent)",
        borderColor: "var(--color-rule-soft)",
      }}
    >
      <div className="mx-auto flex h-[68px] max-w-[1240px] items-center justify-between gap-8 px-6 md:px-8">
        <a href="#top" className="flex items-center gap-2.5">
          <ArbitraWordmark size="md" />
        </a>

        <div className="hidden gap-8 text-[14.5px] font-medium text-[var(--color-ink-soft)] md:flex">
          {links.map(([label, href]) => (
            <a
              key={href}
              href={href}
              className="transition hover:text-[var(--color-ink)]"
            >
              {label}
            </a>
          ))}
        </div>

        <button
          type="button"
          onClick={onWaitlist}
          className="inline-flex h-10 items-center gap-2 rounded-md bg-[var(--color-ink)] px-4 text-[14px] font-medium text-[var(--color-bg)] transition hover:opacity-90"
        >
          Erken erişim <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </nav>
  );
}

/* ============================================================
   01 — HERO (imza anı: yakınsayan jüri + kanıt-çıpası)
   ============================================================ */
function Hero({ onWaitlist }: { onWaitlist: () => void }) {
  return (
    <section id="top" className="relative overflow-hidden pb-20 pt-16 md:pb-24 md:pt-20">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(15,23,42,0.035) 1px, transparent 1px)",
          backgroundSize: "84px 100%",
          maskImage: "linear-gradient(to bottom, black 24%, transparent 92%)",
          WebkitMaskImage:
            "linear-gradient(to bottom, black 24%, transparent 92%)",
        }}
      />
      <div className="relative z-10 mx-auto max-w-[1240px] px-6 md:px-8">
        <div className="grid items-start gap-12 lg:grid-cols-[0.92fr_1.08fr] lg:gap-16">
          {/* SOL — iddia + CTA */}
          <div className="lg:pt-6">
            <div
              className="mb-8 inline-flex items-center gap-2.5 rounded-full border bg-[var(--color-bg-card)] px-3.5 py-1.5 text-[12px] font-medium uppercase tracking-[0.06em] text-[var(--color-ink-soft)]"
              style={{ borderColor: "var(--color-rule)" }}
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: ACCENT }}
              />
              Lansman öncesi · hakemlik provası
            </div>

            <h1
              className="font-display font-medium text-[var(--color-ink)]"
              style={{
                fontSize: "clamp(40px, 5.6vw, 72px)",
                letterSpacing: "-0.018em",
                lineHeight: 1.07,
                marginBottom: 26,
              }}
            >
              Üç bağımsız hakem.
              <br />
              <em className="font-crimson italic" style={{ color: ACCENT }}>
                Tek dürüst yargı.
              </em>
            </h1>

            <p
              className="font-display text-[var(--color-ink-soft)]"
              style={{ fontSize: 20, lineHeight: 1.55, maxWidth: "52ch", marginBottom: 30 }}
            >
              Dergiye göndermeden önce makaleni üç bağımsız hakemin önüne çıkar.
              Önerilen kararı, o yargının{" "}
              <strong className="font-semibold text-[var(--color-ink)]">
                metnindeki hangi cümleye dayandığını
              </strong>{" "}
              ve kabule giden düzeltmeyi birlikte gör — ne kadar güvenilir
              olduğuyla beraber.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={onWaitlist}
                className="inline-flex h-[50px] items-center gap-2 rounded-md bg-[var(--color-ink)] px-6 text-[15.5px] font-medium text-[var(--color-bg)] transition hover:opacity-90 active:translate-y-px"
              >
                Erken erişim listesine katıl <ArrowRight className="h-4 w-4" />
              </button>
              {/* İkincil — örnek raporu gör (dönüşüm CTA'sı değil, keşif). */}
              <Link
                href="/ornek-rapor"
                className="inline-flex h-[50px] items-center gap-2 rounded-md border px-5 text-[15px] font-medium text-[var(--color-ink-soft)] transition hover:text-[var(--color-ink)]"
                style={{ borderColor: "var(--color-rule)" }}
              >
                Örnek raporu gör <Eye className="h-4 w-4" />
              </Link>
            </div>

            <p className="mt-5 font-sans text-[12.5px] text-[var(--color-ink-faint)]">
              Lansman öncesi waitlist · makalen sende kalır · uydurma metrik yok
            </p>
          </div>

          {/* SAĞ — yakınsayan jüri paneli (imza) */}
          <ConvergencePanel />
        </div>

        {/* İMZA — kanıt-çıpası drill (cümle → neden → fix) */}
        <EvidenceAnchor />
      </div>
    </section>
  );
}

/* ── Üç hakem → tek verdict (örnek) ───────────────────────── */
const REVIEWERS = [
  {
    initial: "Y",
    role: "Yöntemci",
    sub: "Yöntem & istatistik",
    read: "Örneklem güç analizine göre sınırda; gruplar arası denge raporlanmamış.",
    lean: "Revizyon gerekli",
    warm: false,
  },
  {
    initial: "Ş",
    role: "Şüpheci",
    sub: "Kanıt & nedensellik",
    read: "Nedensellik dili bulguların ötesine geçiyor; alternatif açıklamalar elenmemiş.",
    lean: "İtirazlı",
    warm: false,
  },
  {
    initial: "Y",
    role: "Yapıcı",
    sub: "Katkı & güçlü yönler",
    read: "Çekirdek katkı net ve özgün; tartışma biraz törpülenirse güçlü.",
    lean: "Kabule yakın",
    warm: true,
  },
] as const;

function ConvergencePanel() {
  return (
    <div
      className="overflow-hidden rounded-xl border bg-[var(--color-bg-card)]"
      style={{
        borderColor: "var(--color-rule)",
        boxShadow:
          "0 1px 0 rgba(15,23,42,0.02), 0 10px 28px -16px rgba(15,23,42,0.14), 0 28px 56px -24px rgba(15,23,42,0.10)",
      }}
    >
      <div
        className="flex items-center justify-between border-b px-4 py-3"
        style={{
          borderColor: "var(--color-rule-soft)",
          background: "var(--color-bg-soft)",
        }}
      >
        <span className="inline-flex items-center gap-1.5 font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-[var(--color-ink-soft)]">
          <span
            className="inline-block h-1.5 w-1.5 rounded-full"
            style={{ background: ACCENT, animation: "advisorPulse 1.8s ease-in-out infinite" }}
          />
          Hakem paneli
        </span>
        <SampleTag />
      </div>

      <div className="p-5">
        {/* üç hakem ayrı ayrı okur */}
        <div className="grid gap-2.5">
          {REVIEWERS.map((r, i) => (
            <div
              key={i}
              className="flex items-start gap-3 rounded-lg border p-3"
              style={{ borderColor: "var(--color-rule-soft)" }}
            >
              <div
                className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border font-display text-[14px] font-medium italic text-[var(--color-ink)]"
                style={{ borderColor: "var(--color-rule)", background: "var(--color-bg)" }}
              >
                {r.initial}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-display text-[15px] font-medium text-[var(--color-ink)]">
                    {r.role}
                    <span className="ml-2 font-sans text-[11px] font-normal text-[var(--color-ink-faint)]">
                      {r.sub}
                    </span>
                  </span>
                  <span
                    className="flex-shrink-0 font-sans text-[11px] font-medium uppercase tracking-[0.04em]"
                    style={{ color: r.warm ? ACCENT : "var(--color-ink-mute)" }}
                  >
                    {r.lean}
                  </span>
                </div>
                <p className="mt-1 font-display text-[14px] leading-snug text-[var(--color-ink-soft)]">
                  {r.read}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* yakınsama → tek verdict */}
        <div className="mt-3 flex items-center gap-3 px-1">
          <span className="h-px flex-1" style={{ background: "var(--color-rule-soft)" }} />
          <span className="font-sans text-[10.5px] font-medium uppercase tracking-[0.12em] text-[var(--color-ink-faint)]">
            yakınsar
          </span>
          <span className="h-px flex-1" style={{ background: "var(--color-rule-soft)" }} />
        </div>

        <div
          className="mt-3 rounded-lg border p-4"
          style={{
            borderColor: "var(--color-ink)",
            background: "var(--color-ink)",
            color: "var(--color-bg)",
          }}
        >
          <div className="flex items-center justify-between">
            <span className="font-sans text-[11px] font-medium uppercase tracking-[0.12em]"
              style={{ color: "color-mix(in oklab, var(--color-bg) 64%, transparent)" }}>
              Önerilen karar
            </span>
            <span
              className="rounded-full px-2.5 py-0.5 font-sans text-[12px] font-semibold uppercase tracking-[0.04em]"
              style={{ background: ACCENT, color: "var(--color-accent-fg)" }}
            >
              Majör revizyon
            </span>
          </div>
          <p className="mt-2.5 font-display text-[16px] leading-snug">
            Çekirdek katkı sağlam; ancak yöntem gerekçesi ve nedensellik dili
            kabul için düzeltilmeli.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Kanıt-çıpası: cümle → neden → fix (interaktif, statik fallback) ── */
const FINDINGS = [
  {
    tag: "Nedensellik dili",
    severity: "Majör",
    quote:
      "“Müdahale, öğrenme çıktılarını anlamlı biçimde artırdı ve bu etkiyi doğrudan programa bağlıyoruz.”",
    why: "Bulgu–iddia uyumu: gözlemsel desen, doğrudan nedensellik iddiasını taşıyamaz; karıştırıcı değişkenler elenmemiş.",
    dimension: "Kanıt / Nedensellik",
    fix: "“ilişkilidir / işaret etmektedir” diline geç; olası karıştırıcıları sınırlılıklarda tartış.",
    accept: "Kabul ölçütü: doğrudan nedensel ifade kalmamalı.",
  },
  {
    tag: "Örneklem gerekçesi",
    severity: "Majör",
    quote: "“Çalışmaya toplam 48 katılımcı dâhil edilmiştir.”",
    why: "İstatistiksel güç: beklenen etki büyüklüğü için a priori güç analizi raporlanmamış.",
    dimension: "Yöntem / İstatistik",
    fix: "Etki büyüklüğü, α ve 1−β ile güç analizini ekle; örneklem gerekçesini netleştir.",
    accept: "Kabul ölçütü: hedef güç ≥ .80 gerekçelendirilmiş.",
  },
] as const;

function EvidenceAnchor() {
  const [active, setActive] = useState(0);
  const f = FINDINGS[active]!;
  return (
    <div
      className="mt-14 overflow-hidden rounded-xl border bg-[var(--color-bg-card)] md:mt-20"
      style={{ borderColor: "var(--color-rule)" }}
    >
      <div
        className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3.5"
        style={{ borderColor: "var(--color-rule-soft)", background: "var(--color-bg-soft)" }}
      >
        <span className="font-display text-[15px] font-medium text-[var(--color-ink)]">
          Her yargı, metnindeki bir cümleye çıpalı.
          <span className="ml-2 font-sans text-[12px] font-normal text-[var(--color-ink-faint)]">
            bir bulguya dokun
          </span>
        </span>
        <SampleTag />
      </div>

      <div className="grid md:grid-cols-[0.8fr_1.2fr]">
        {/* bulgu seçici */}
        <div
          className="flex flex-col gap-2 border-b p-4 md:border-b-0 md:border-r"
          style={{ borderColor: "var(--color-rule-soft)" }}
        >
          {FINDINGS.map((item, i) => {
            const selected = i === active;
            return (
              <button
                key={item.tag}
                type="button"
                onClick={() => setActive(i)}
                onMouseEnter={() => setActive(i)}
                aria-pressed={selected}
                className="rounded-lg border p-3 text-left transition"
                style={{
                  borderColor: selected ? "var(--color-ink)" : "var(--color-rule-soft)",
                  background: selected ? "var(--color-bg)" : "transparent",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-display text-[15px] font-medium text-[var(--color-ink)]">
                    {item.tag}
                  </span>
                  <span
                    className="rounded-full border px-2 py-0.5 font-sans text-[10.5px] font-medium uppercase tracking-[0.06em]"
                    style={{
                      color: "var(--color-warn)",
                      borderColor: "color-mix(in oklab, var(--color-warn) 40%, transparent)",
                    }}
                  >
                    {item.severity}
                  </span>
                </div>
                <span className="mt-1 block font-sans text-[12px] text-[var(--color-ink-faint)]">
                  {item.dimension}
                </span>
              </button>
            );
          })}
        </div>

        {/* üç katman: cümle → neden → fix */}
        <div className="grid gap-px bg-[var(--color-rule-soft)] sm:grid-cols-3">
          <AnchorLayer
            step="01"
            label="Makaledeki cümle"
            icon={<Quote className="h-3.5 w-3.5" />}
          >
            <p className="font-crimson text-[15px] italic leading-snug text-[var(--color-ink)]">
              {f.quote}
            </p>
          </AnchorLayer>
          <AnchorLayer
            step="02"
            label="Neden — kriter"
            icon={<AlertCircle className="h-3.5 w-3.5" />}
          >
            <p className="font-display text-[14px] leading-snug text-[var(--color-ink-soft)]">
              {f.why}
            </p>
          </AnchorLayer>
          <AnchorLayer
            step="03"
            label="Kabule fix"
            icon={<Check className="h-3.5 w-3.5" />}
            accent
          >
            <p className="font-display text-[14px] leading-snug text-[var(--color-ink)]">
              {f.fix}
            </p>
            <p className="mt-2 font-sans text-[12px] font-medium" style={{ color: ACCENT }}>
              {f.accept}
            </p>
          </AnchorLayer>
        </div>
      </div>
    </div>
  );
}

function AnchorLayer({
  step,
  label,
  icon,
  accent = false,
  children,
}: {
  step: string;
  label: string;
  icon: React.ReactNode;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-[var(--color-bg-card)] p-5">
      <div className="mb-3 flex items-center gap-2">
        <span
          className="inline-flex h-6 w-6 items-center justify-center rounded-full"
          style={{
            background: accent ? ACCENT : "var(--color-bg-soft)",
            color: accent ? "var(--color-accent-fg)" : "var(--color-ink-mute)",
          }}
        >
          {icon}
        </span>
        <span className="font-sans text-[11px] font-medium uppercase tracking-[0.1em] text-[var(--color-ink-faint)]">
          <span className="mr-1.5 font-semibold" style={{ color: ACCENT }}>
            {step}
          </span>
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

/* ============================================================
   SECTION HEAD — § 0X kicker + display başlık + deck
   ============================================================ */
function SectionHead({
  num,
  kicker,
  title,
  deck,
  centered = false,
  onDark = false,
}: {
  num: string;
  kicker: string;
  title: React.ReactNode;
  deck?: React.ReactNode;
  centered?: boolean;
  onDark?: boolean;
}) {
  return (
    <div
      className={
        centered
          ? "mb-12 text-center"
          : "mb-12 grid items-end gap-10 md:mb-16 md:grid-cols-[0.85fr_1.15fr] md:gap-14"
      }
    >
      <div>
        <div
          className="font-sans text-[12px] font-medium uppercase tracking-[0.12em]"
          style={{
            color: onDark
              ? "color-mix(in oklab, var(--color-bg) 60%, transparent)"
              : "var(--color-ink-faint)",
          }}
        >
          <span
            className="mr-2 font-semibold"
            style={{ color: onDark ? "var(--color-accent-soft)" : ACCENT }}
          >
            § {num}
          </span>
          {kicker}
        </div>
        <h2
          className="mt-3.5 font-display text-[clamp(32px,4vw,50px)] font-medium leading-[1.08]"
          style={{
            letterSpacing: "-0.02em",
            color: onDark ? "var(--color-bg)" : "var(--color-ink)",
          }}
        >
          {title}
        </h2>
      </div>
      {deck && (
        <div
          className="font-display text-[18px] leading-[1.55]"
          style={{
            color: onDark
              ? "color-mix(in oklab, var(--color-bg) 78%, transparent)"
              : "var(--color-ink-soft)",
            maxWidth: "52ch",
          }}
        >
          {deck}
        </div>
      )}
    </div>
  );
}

/* ============================================================
   02 — NASIL ÇALIŞIR (gerçek hat: parse→atıf→bağlam→kapsam→council)
   ============================================================ */
const READ_STAGES = [
  ["Ayrıştırma", "metin & yapı"],
  ["Atıf bütünlüğü", "kaynak ↔ iddia"],
  ["Bağlam", "literatür yeri"],
  ["Kapsam", "boşluk taraması"],
  ["Hakem paneli", "council"],
] as const;

const FLOW_STEPS = [
  {
    h: "Yükle",
    p: "Makaleni (PDF/DOCX) yükle. Metnin işlenir, ama sende kalır — dış servise gönderim için ayrı rıza gerekir.",
  },
  {
    h: "Panel okur",
    p: "Aşağıdaki okuma hattı sırayla işler; her aşama izlenebilir. Sonunda üç hakem ayrı ayrı değerlendirir.",
  },
  {
    h: "Yargı + çıpalı bulgu",
    p: "Önerilen karar ve tek-cümle teşhis gelir. Her bulgu, makalendeki tam cümleye ve bir kritere çıpalıdır.",
  },
  {
    h: "Kabule fix",
    p: "Her bulgunun bir düzeltmesi ve bir kabul ölçütü vardır — neyi değiştirince geçtiğini bilirsin.",
  },
] as const;

function HowItWorks() {
  return (
    <section id="nasil-calisir" className="py-24 md:py-32">
      <div className="mx-auto max-w-[1240px] px-6 md:px-8">
        <SectionHead
          num="02"
          kicker="Nasıl çalışır"
          title={
            <>
              Yükle, panel okusun,{" "}
              <em className="font-crimson italic">kabule kadar düzelt.</em>
            </>
          }
          deck={
            <>
              Tek bir &ldquo;skor&rdquo; üretmez. Makaleni gerçek bir hakem gibi
              katman katman okur; yargısını metnindeki cümlelere çıpalar ve her
              eleştiri için kabule giden somut bir adım verir.
            </>
          }
        />

        {/* okuma hattı */}
        <div
          className="mb-12 overflow-hidden rounded-xl border bg-[var(--color-bg-card)]"
          style={{ borderColor: "var(--color-rule-soft)" }}
        >
          <div
            className="border-b px-5 py-3 font-sans text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--color-ink-faint)]"
            style={{ borderColor: "var(--color-rule-soft)", background: "var(--color-bg-soft)" }}
          >
            Okuma hattı
          </div>
          <div className="grid grid-cols-2 gap-px bg-[var(--color-rule-soft)] sm:grid-cols-3 lg:grid-cols-5">
            {READ_STAGES.map(([h, sub], i) => (
              <div key={h} className="bg-[var(--color-bg-card)] p-5">
                <div className="font-mono-pmid text-[11px] text-[var(--color-ink-faint)]">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="mt-2 font-display text-[17px] font-medium text-[var(--color-ink)]">
                  {h}
                </div>
                <div className="mt-1 font-sans text-[12.5px] text-[var(--color-ink-faint)]">
                  {sub}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* sonuç akışı */}
        <div className="grid grid-cols-1 gap-10 md:grid-cols-4 md:gap-8">
          {FLOW_STEPS.map((s, i) => (
            <div key={i}>
              <div
                className="font-crimson italic font-medium leading-none"
                style={{ fontSize: 64, color: ACCENT, letterSpacing: "-0.04em" }}
              >
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="relative my-5 h-px" style={{ background: "var(--color-rule-soft)" }}>
                <span
                  className="absolute left-0 top-0 h-px w-9"
                  style={{ background: "var(--color-ink)" }}
                />
              </div>
              <h3
                className="mb-2.5 font-display text-[21px] font-medium leading-[1.2] text-[var(--color-ink)]"
                style={{ letterSpacing: "-0.015em" }}
              >
                {s.h}
              </h3>
              <p className="m-0 max-w-[34ch] font-display text-[15.5px] leading-[1.55] text-[var(--color-ink-soft)]">
                {s.p}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   03 — PANEL (dark jüri, 3 gerçek persona)
   ============================================================ */
function Jury() {
  const reviewers = [
    {
      avatar: "Y",
      role: "Yöntemci",
      sub: "Yöntem & istatistik",
      stance: "Şüpheci",
      warm: false,
      quote:
        "Örneklem güç analizine göre sınırda; gruplar arası dağılım dengesiz görünüyor. Katmanlı örnekleme ve a priori güç analizi raporlanmalı.",
      verdict: "Majör revizyon",
      verdictAccent: false,
    },
    {
      avatar: "Ş",
      role: "Şüpheci",
      sub: "Kanıt & nedensellik",
      stance: "İtirazlı",
      warm: false,
      quote:
        "Sonuç bölümünde nedensellik dili, gözlemsel desenin taşıyabileceğinin ötesinde. Alternatif açıklamalar ve karıştırıcılar elenmeden bu iddia savunulamaz.",
      verdict: "İtirazlı",
      verdictAccent: false,
    },
    {
      avatar: "Y",
      role: "Yapıcı",
      sub: "Katkı & güçlü yönler",
      stance: "Yapıcı",
      warm: true,
      quote:
        "Çekirdek katkı net ve alana özgün. Tartışmada iddia dili ölçülenirse ve sınırlılıklar dürüstçe yazılırsa, çalışma kabule güçlü bir aday.",
      verdict: "Kabule yakın",
      verdictAccent: true,
    },
  ];

  return (
    <section id="panel" className="py-24 md:py-32" style={{ background: "var(--color-ink)" }}>
      <div className="mx-auto max-w-[1240px] px-6 md:px-8">
        <SectionHead
          onDark
          num="03"
          kicker="Panel — örnek değerlendirme"
          title={
            <>
              Üç hakem, üç bakış.{" "}
              <em className="font-crimson italic">Aynı metin, ayrı vicdan.</em>
            </>
          }
          deck={
            <>
              Tek bir modelin tek sesi yerine üç bağımsız persona ayrı ayrı okur:
              yöntemi sorgulayan, iddiaya direnen ve katkıyı güçlendiren. Roller
              gerçek değerlendirme motorundan gelir — uydurma itiraz yok.
            </>
          }
        />

        <div
          className="grid grid-cols-1 gap-px border md:grid-cols-3"
          style={{
            background: "color-mix(in oklab, var(--color-bg) 14%, var(--color-ink))",
            borderColor: "color-mix(in oklab, var(--color-bg) 14%, var(--color-ink))",
          }}
        >
          {reviewers.map((r, i) => (
            <div key={i} className="p-8" style={{ background: "var(--color-ink)" }}>
              <div
                className="mb-5 flex items-center justify-between border-b pb-4"
                style={{ borderColor: "color-mix(in oklab, var(--color-bg) 18%, var(--color-ink))" }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-full border font-display text-[18px] font-medium italic text-[var(--color-bg)]"
                    style={{
                      background: "color-mix(in oklab, var(--color-bg) 12%, var(--color-ink))",
                      borderColor: "color-mix(in oklab, var(--color-bg) 22%, var(--color-ink))",
                    }}
                  >
                    {r.avatar}
                  </div>
                  <div
                    className="font-sans text-[11.5px] font-medium uppercase tracking-[0.1em]"
                    style={{ color: "color-mix(in oklab, var(--color-bg) 70%, transparent)" }}
                  >
                    {r.sub}
                    <strong
                      className="mt-0.5 block font-display text-[17px] font-medium normal-case tracking-tight"
                      style={{ color: "var(--color-bg)", letterSpacing: "-0.005em" }}
                    >
                      {r.role}
                    </strong>
                  </div>
                </div>
                <span
                  className="rounded-full border px-2.5 py-1 font-sans text-[11px] font-medium uppercase tracking-[0.08em]"
                  style={{
                    color: r.warm
                      ? "var(--color-accent-soft)"
                      : "color-mix(in oklab, var(--color-bg) 80%, transparent)",
                    borderColor: r.warm
                      ? "color-mix(in oklab, var(--color-accent) 50%, transparent)"
                      : "color-mix(in oklab, var(--color-bg) 22%, var(--color-ink))",
                  }}
                >
                  {r.stance}
                </span>
              </div>

              <blockquote
                className="m-0 font-display text-[19px] font-normal leading-[1.45] text-[var(--color-bg)]"
                style={{ letterSpacing: "-0.005em" }}
              >
                <span
                  className="mb-3 block font-display"
                  style={{ fontSize: 52, lineHeight: 0.6, color: "var(--color-accent-soft)" }}
                >
                  &ldquo;
                </span>
                {r.quote}
              </blockquote>

              <div
                className="mt-6 flex items-baseline justify-between border-t pt-5"
                style={{ borderColor: "color-mix(in oklab, var(--color-bg) 12%, var(--color-ink))" }}
              >
                <span
                  className="font-sans text-[11px] font-medium uppercase tracking-[0.1em]"
                  style={{ color: "color-mix(in oklab, var(--color-bg) 60%, transparent)" }}
                >
                  Eğilim
                </span>
                <span
                  className="font-display text-[17px] font-medium"
                  style={{ color: r.verdictAccent ? "var(--color-accent-soft)" : "var(--color-bg)" }}
                >
                  {r.verdict}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   04 — DÜRÜSTLÜK KATMANI (sakladığımız değil, gösterdiğimiz)
   ============================================================ */
const HONESTY_ITEMS = [
  {
    icon: <Eye className="h-4 w-4" />,
    h: "Güven aralığı",
    p: "Her yargının ne kadar güvenilir olduğunu işaretleriz — yüksek/orta/düşük. Yargı tek başına gelmez.",
  },
  {
    icon: <AlertCircle className="h-4 w-4" />,
    h: "Sınırlılıklar",
    p: "Neyi değerlendiremediğimizi açıkça yazarız. Eksik veri veya kapalı tam-metin gizlenmez.",
  },
  {
    icon: <FileText className="h-4 w-4" />,
    h: "UNVERIFIED çıpa",
    p: "Bir cümleyi metninde birebir doğrulayamadıysak, o çıpayı “doğrulanamadı” diye işaretleriz — sahte güven üretmeyiz.",
  },
  {
    icon: <Shield className="h-4 w-4" />,
    h: "Bozulma & tekrar",
    p: "Bir aşama düşük kapasiteyle çalıştıysa veya yargı yeniden üretilebilir değilse, bunu raporun yüzünde söyleriz.",
  },
];

function Honesty() {
  return (
    <section id="durustluk" className="py-24 md:py-32">
      <div className="mx-auto max-w-[1240px] px-6 md:px-8">
        <SectionHead
          num="04"
          kicker="Dürüstlük katmanı"
          title={
            <>
              Belirsizliği saklamayız.{" "}
              <em className="font-crimson italic">Gösteririz.</em>
            </>
          }
          deck={
            <>
              Çoğu araç emin görünmek için belirsizliği gizler. Biz tam tersini
              yaparız: yargıyı, onun ne kadar güvenilir olduğuyla birlikte
              veririz. Asıl fark burada.
            </>
          }
        />

        <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
          <div className="grid grid-cols-1 gap-px border sm:grid-cols-2"
            style={{ background: "var(--color-rule-soft)", borderColor: "var(--color-rule-soft)" }}>
            {HONESTY_ITEMS.map((it, i) => (
              <div key={i} className="bg-[var(--color-bg)] p-7">
                <span
                  className="inline-flex h-9 w-9 items-center justify-center rounded-full"
                  style={{ background: "var(--color-accent-pale)", color: ACCENT }}
                >
                  {it.icon}
                </span>
                <h3 className="mt-4 font-display text-[19px] font-medium text-[var(--color-ink)]">
                  {it.h}
                </h3>
                <p className="mt-2 font-display text-[15px] leading-[1.55] text-[var(--color-ink-soft)]">
                  {it.p}
                </p>
              </div>
            ))}
          </div>

          {/* örnek dürüstlük çıpası */}
          <div
            className="self-start rounded-xl border bg-[var(--color-bg-card)] p-6"
            style={{ borderColor: "var(--color-rule)" }}
          >
            <div className="mb-4 flex items-center justify-between">
              <span className="font-display text-[16px] font-medium text-[var(--color-ink)]">
                Rapor üzerinde nasıl görünür
              </span>
              <SampleTag />
            </div>

            <div
              className="rounded-lg border p-4"
              style={{ borderColor: "var(--color-rule-soft)", background: "var(--color-bg)" }}
            >
              <p className="font-crimson text-[15px] italic leading-snug text-[var(--color-ink)]">
                {"“…etki tüm alt gruplarda tutarlıdır.”"}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span
                  className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-sans text-[11px] font-medium uppercase tracking-[0.06em]"
                  style={{
                    color: "var(--color-warn)",
                    borderColor: "color-mix(in oklab, var(--color-warn) 40%, transparent)",
                  }}
                >
                  <AlertCircle className="h-3 w-3" /> Doğrulanamadı
                </span>
                <span className="font-sans text-[12px] text-[var(--color-ink-faint)]">
                  Bu cümle metinde birebir bulunamadı.
                </span>
              </div>
            </div>

            <div className="mt-4 space-y-2.5">
              <ConfidenceRow label="Güven aralığı" value="Orta" tone="warn" />
              <ConfidenceRow label="Yargı tekrar üretilebilir" value="Evet" tone="ok" />
              <ConfidenceRow label="Tam metin erişimi" value="Kısmi" tone="warn" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ConfidenceRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "ok" | "warn";
}) {
  const color = tone === "ok" ? "var(--color-ok)" : "var(--color-warn)";
  return (
    <div className="flex items-center justify-between">
      <span className="font-sans text-[13px] text-[var(--color-ink-soft)]">{label}</span>
      <span
        className="rounded-full px-2.5 py-0.5 font-sans text-[12px] font-medium"
        style={{
          color,
          background: `color-mix(in oklab, ${color} 12%, var(--color-bg-card))`,
        }}
      >
        {value}
      </span>
    </div>
  );
}

/* ============================================================
   05 — GİZLİLİK & KVKK (gerçek özellikler)
   ============================================================ */
const PRIVACY_ITEMS = [
  {
    icon: <Lock className="h-5 w-5" />,
    h: "Makalen gizlidir",
    p: "Yüklediğin metin sana aittir. Başkasının erişimine açılmaz, eğitim verisi olarak kullanılmaz.",
  },
  {
    icon: <Shield className="h-5 w-5" />,
    h: "Dış-AI rıza kapısı",
    p: "Metnin bir dış yapay-zekâ servisine gönderilecekse, bu ancak senin açık onayınla olur. Onay yoksa gönderilmez.",
  },
  {
    icon: <Trash2 className="h-5 w-5" />,
    h: "Süre sonunda otomatik silinir",
    p: "Saklama süresi dolduğunda makalen sistemden otomatik silinir. Bu bir vaat değil; veritabanına yazılı bir kuraldır.",
  },
];

function Privacy() {
  return (
    <section
      id="gizlilik"
      className="border-y py-24 md:py-32"
      style={{ borderColor: "var(--color-rule-soft)", background: "var(--color-bg-soft)" }}
    >
      <div className="mx-auto max-w-[1240px] px-6 md:px-8">
        <SectionHead
          num="05"
          kicker="Gizlilik & KVKK"
          title={
            <>
              Yüklemeden önce{" "}
              <em className="font-crimson italic">güvenmen gerekir.</em>
            </>
          }
          deck={
            <>
              Yayımlanmamış bir makale hassas bir emanettir. Gizlilik bizde bir
              pazarlama cümlesi değil, koda gömülü bir davranış — rıza kapısı ve
              otomatik silme dâhil.
            </>
          }
        />

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {PRIVACY_ITEMS.map((it, i) => (
            <div
              key={i}
              className="rounded-xl border bg-[var(--color-bg-card)] p-8"
              style={{ borderColor: "var(--color-rule-soft)" }}
            >
              <span
                className="inline-flex h-11 w-11 items-center justify-center rounded-xl"
                style={{ background: "var(--color-accent-pale)", color: ACCENT }}
              >
                {it.icon}
              </span>
              <h3 className="mt-5 font-display text-[21px] font-medium text-[var(--color-ink)]">
                {it.h}
              </h3>
              <p className="mt-2.5 font-display text-[15.5px] leading-[1.55] text-[var(--color-ink-soft)]">
                {it.p}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   06 — KARŞILAŞTIRMA (kategori bazlı, adil — uydurma rakip iddiası yok)
   ============================================================ */
function Compare() {
  const cols = ["Genel AI sohbeti", "Tek-model araçlar", BRAND];
  const rows: { feat: string; vals: (boolean | "partial")[] }[] = [
    { feat: "Yargıyı metnindeki cümleye çıpalar", vals: [false, "partial", true] },
    { feat: "Belirsizliği / UNVERIFIED açıkça gösterir", vals: [false, false, true] },
    { feat: "Çok-hakemli bağımsız panel", vals: [false, false, true] },
    { feat: "Her bulguya fix + kabul ölçütü", vals: ["partial", "partial", true] },
    { feat: "Türkçe akademik dile özgü", vals: ["partial", false, true] },
  ];

  const renderVal = (v: boolean | "partial", isArbitra: boolean) => {
    if (v === true)
      return (
        <span
          className="inline-flex h-6 w-6 items-center justify-center rounded-full"
          style={{
            background: isArbitra ? ACCENT : "var(--color-ink)",
            color: isArbitra ? "var(--color-accent-fg)" : "var(--color-bg)",
          }}
        >
          <Check className="h-3 w-3" strokeWidth={3} />
        </span>
      );
    if (v === "partial")
      return (
        <span className="font-sans text-[12px] font-medium text-[var(--color-ink-faint)]">
          kısmi
        </span>
      );
    return (
      <span
        className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--color-ink-faint)]"
        style={{ background: "var(--color-bg-soft)" }}
      >
        <X className="h-3.5 w-3.5" />
      </span>
    );
  };

  return (
    <section id="karsilastirma" className="py-24 md:py-32">
      <div className="mx-auto max-w-[1240px] px-6 md:px-8">
        <SectionHead
          num="06"
          kicker="Neden Arbitra"
          title={
            <>
              Cevap üretmez.{" "}
              <em className="font-crimson italic">Hakemler gibi yargılar.</em>
            </>
          }
          deck={
            <>
              Genel bir AI sohbeti güvenle konuşur ama yargısını metnine
              dayandırmaz; tek-model araçlar tek ses verir. Arbitra üç bağımsız
              hakemi, çıpalı yargıyı ve dürüst belirsizliği bir araya getirir.
            </>
          }
        />

        <div
          className="overflow-x-auto rounded-xl border bg-[var(--color-bg-card)]"
          style={{ borderColor: "var(--color-rule-soft)" }}
        >
          <table className="w-full border-collapse text-[14.5px]">
            <thead>
              <tr>
                <th
                  className="border-b bg-[var(--color-bg-soft)] px-5 py-4 text-left font-display text-[16px] font-medium text-[var(--color-ink)]"
                  style={{ borderColor: "var(--color-rule-soft)" }}
                >
                  Yetenek
                </th>
                {cols.map((c, i) => {
                  const isArbitra = i === cols.length - 1;
                  return (
                    <th
                      key={c}
                      className="relative border-b px-5 py-4 text-center font-sans text-[12px] font-medium uppercase tracking-[0.08em]"
                      style={{
                        borderColor: "var(--color-rule-soft)",
                        background: isArbitra ? "var(--color-ink)" : "var(--color-bg-soft)",
                        color: isArbitra ? "var(--color-bg)" : "var(--color-ink-faint)",
                      }}
                    >
                      {isArbitra ? (
                        <span className="inline-flex normal-case tracking-tight">
                          <ArbitraWordmark size="sm" className="!text-[var(--color-bg)]" />
                        </span>
                      ) : (
                        c
                      )}
                      {isArbitra && (
                        <span
                          aria-hidden
                          className="absolute inset-x-0 -bottom-px h-0.5"
                          style={{ background: ACCENT }}
                        />
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => {
                const last = ri === rows.length - 1;
                return (
                  <tr key={ri}>
                    <th
                      scope="row"
                      className="border-b px-5 py-4 text-left font-display text-[16px] font-medium text-[var(--color-ink)]"
                      style={{ borderColor: last ? "transparent" : "var(--color-rule-soft)" }}
                    >
                      {r.feat}
                    </th>
                    {r.vals.map((v, ci) => {
                      const isArbitra = ci === r.vals.length - 1;
                      return (
                        <td
                          key={ci}
                          className="border-b px-5 py-4 text-center"
                          style={{
                            borderColor: last ? "transparent" : "var(--color-rule-soft)",
                            background: isArbitra
                              ? "color-mix(in oklab, var(--color-accent) 7%, var(--color-bg-card))"
                              : undefined,
                          }}
                        >
                          {renderVal(v, isArbitra)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-4 font-sans text-[12.5px] text-[var(--color-ink-faint)]">
          Karşılaştırma kategori düzeyindedir; belirli ürünler hakkında iddia
          içermez. &ldquo;Kısmi&rdquo; = yaklaşıma göre değişir.
        </p>
      </div>
    </section>
  );
}

/* ============================================================
   07 — CTA / WAITLIST (tek dönüşüm; fiyat erken-erişime katlandı)
   ============================================================ */
function Cta({ onWaitlist }: { onWaitlist: () => void }) {
  return (
    <section
      id="cta"
      className="border-t py-24 text-center md:py-32"
      style={{ borderColor: "var(--color-rule-soft)", background: "var(--color-ink)" }}
    >
      <div className="mx-auto max-w-[820px] px-6 md:px-8">
        <h2
          className="mx-auto font-display font-medium"
          style={{
            fontSize: "clamp(38px, 5vw, 64px)",
            letterSpacing: "-0.02em",
            lineHeight: 1.08,
            color: "var(--color-bg)",
            marginBottom: 22,
          }}
        >
          Göndermeden önce,{" "}
          <em className="font-crimson italic" style={{ color: "var(--color-accent-soft)" }}>
            bağımsız hakem.
          </em>
        </h2>
        <p
          className="mx-auto font-display text-[18px] leading-[1.55]"
          style={{
            color: "color-mix(in oklab, var(--color-bg) 78%, transparent)",
            maxWidth: "52ch",
            marginBottom: 32,
          }}
        >
          {BRAND} lansman öncesi. Erken erişim listesine katıl; hazır olduğunda
          ilk sen haberdar ol. Fiyatlandırma erken erişimde netleşecek — şimdi
          taahhüt yok.
        </p>
        <button
          type="button"
          onClick={onWaitlist}
          className="inline-flex h-[52px] items-center gap-2 rounded-md px-7 font-sans text-[15.5px] font-medium transition hover:opacity-90 active:translate-y-px"
          style={{ background: ACCENT, color: "var(--color-accent-fg)" }}
        >
          Erken erişim listesine katıl <ArrowRight className="h-4 w-4" />
        </button>
        <p
          className="mt-6 font-sans text-[12px] font-medium uppercase tracking-[0.12em]"
          style={{ color: "color-mix(in oklab, var(--color-bg) 55%, transparent)" }}
        >
          Türkçe öncelikli · spam yok · makalen sende kalır
        </p>
      </div>
    </section>
  );
}

/* ============================================================
   FOOTER (lean, honest — ölü link yok)
   ============================================================ */
function Footer() {
  const nav = [
    ["Nasıl çalışır", "#nasil-calisir"],
    ["Panel", "#panel"],
    ["Dürüstlük", "#durustluk"],
    ["Gizlilik & KVKK", "#gizlilik"],
    ["Karşılaştırma", "#karsilastirma"],
  ];
  return (
    <footer
      className="pb-8 pt-16"
      style={{
        background: "var(--color-ink)",
        color: "color-mix(in oklab, var(--color-bg) 75%, transparent)",
        borderTop: "1px solid color-mix(in oklab, var(--color-bg) 12%, transparent)",
      }}
    >
      <div className="mx-auto max-w-[1240px] px-6 md:px-8">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-[1.6fr_1fr]">
          <div>
            <a href="#top" className="inline-flex items-center">
              <ArbitraWordmark size="lg" className="!text-[var(--color-bg)]" />
            </a>
            <p
              className="mt-3 max-w-[34ch] font-crimson italic"
              style={{
                fontSize: 17,
                lineHeight: 1.55,
                color: "color-mix(in oklab, var(--color-bg) 80%, transparent)",
              }}
            >
              {BRAND_TAGLINE_TR} Üç bağımsız hakem, çıpalı yargı, dürüst
              belirsizlik.
            </p>
          </div>
          <div>
            <p
              className="mb-4 font-sans text-[11px] font-medium uppercase tracking-[0.12em]"
              style={{ color: "color-mix(in oklab, var(--color-bg) 55%, transparent)" }}
            >
              Sayfada
            </p>
            <ul className="m-0 grid grid-cols-2 gap-2.5 p-0 font-sans text-[14px]">
              {nav.map(([label, href]) => (
                <li key={href}>
                  <a href={href} className="transition hover:text-[var(--color-bg)]">
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div
          className="mt-14 border-t pt-6 font-sans text-[12px] tracking-tight"
          style={{
            borderColor: "color-mix(in oklab, var(--color-bg) 12%, transparent)",
            color: "color-mix(in oklab, var(--color-bg) 55%, transparent)",
          }}
        >
          © 2026 {BRAND} · Gaziantep, TR
        </div>
      </div>
    </footer>
  );
}

/* ============================================================
   PAGE
   ============================================================ */
export default function LandingPage() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [waitlistSource, setWaitlistSource] = useState<WaitlistSource>("landing_hero");

  const openWaitlist = (source: WaitlistSource) => {
    setWaitlistSource(source);
    setWaitlistOpen(true);
  };

  return (
    <>
      <SplashOverlay />
      <main
        className="font-display"
        style={{
          background: "var(--color-bg)",
          color: "var(--color-ink-soft)",
          fontSize: 18,
          lineHeight: 1.65,
        }}
      >
        <Nav onWaitlist={() => openWaitlist("landing_hero")} />
        <Hero onWaitlist={() => openWaitlist("landing_hero")} />
        <HowItWorks />
        <Jury />
        <Honesty />
        <Privacy />
        <Compare />
        <Cta onWaitlist={() => openWaitlist("landing_pricing")} />
        <Footer />
      </main>
      <WaitlistModal
        open={waitlistOpen}
        source={waitlistSource}
        onClose={() => setWaitlistOpen(false)}
      />
    </>
  );
}
