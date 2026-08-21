"use client";

import { useEffect, useRef } from "react";

// F4 ad-hoc P080 — defense-5 (Jüri & Hakem Simülasyonu) açılış perde animasyonu.
// Mockup: D17-SimulationCurtain.html (canon). Class-toggle pattern (D17 native, Framer Motion yok).
// Timeline: 0s blackout → 0.7s curtain açılır → 2.1s jüri fade-in → 2.8s spotlight → 3.8s typewriter → ~7s bitiş.
// Usage:
//   const [showCurtain, setShowCurtain] = useState(true);
//   {showCurtain && <SimulationCurtain onComplete={() => setShowCurtain(false)} />}
// İlk ziyaret algı: sessionStorage "pm_simulation_seen". prefers-reduced-motion → final state direkt.

const OPENING_LINE =
  "Oturumu açıyorum. Sayın aday, çalışmanızı sunmaya hazır olduğunuzda başlayabilirsiniz.";
const SESSION_KEY = "pm_simulation_seen";
const TYPEWRITER_MS = 32;

interface Props {
  onComplete: () => void;
}

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function SimulationCurtain({ onComplete }: Props) {
  const blackoutRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const curtainRef = useRef<HTMLDivElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const transcriptTextRef = useRef<HTMLSpanElement>(null);
  const skipBtnRef = useRef<HTMLButtonElement>(null);
  const replayBtnRef = useRef<HTMLButtonElement>(null);
  // Per-run generation token — shared boolean cancellation race'ini eler (Konsey 2026-05-01).
  // Her runStart artan gen alır; her await sonrası gen ≠ runGenRef.current ise drop.
  // Skip/Replay artan gen ile in-flight chain'leri otomatik invalidate eder.
  const runGenRef = useRef(0);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  // Tek useEffect — sessionStorage gate + animasyon kickoff. setState yok (lint react-hooks/set-state-in-effect).
  // İlk render statik (curtain kapalı, blackout=0, jury opacity=0) → SSR-safe, hydration mismatch yok.
  // Seen ise: useEffect onComplete çağırır, parent component unmount eder.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const seen = window.sessionStorage.getItem(SESSION_KEY) === "1";
    if (seen) {
      onCompleteRef.current();
      return;
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      applyFinalState();
      finish();
    } else {
      void runStart();
    }
    return () => {
      // unmount → tüm in-flight chain'ler invalid. Ref counter (DOM node değil),
      // exhaustive-deps "stale ref" uyarısı bu pattern için geçerli değil.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      runGenRef.current++;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyFinalState() {
    if (transcriptTextRef.current) transcriptTextRef.current.textContent = OPENING_LINE;
    curtainRef.current?.classList.add("open");
    stageRef.current?.classList.add("jury-visible", "spotlight-on");
    transcriptRef.current?.classList.add("visible");
    blackoutRef.current?.classList.remove("active");
    if (skipBtnRef.current) {
      skipBtnRef.current.style.opacity = "0";
      skipBtnRef.current.style.pointerEvents = "none";
    }
    replayBtnRef.current?.classList.add("visible");
  }

  function finish() {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(SESSION_KEY, "1");
    }
    onCompleteRef.current();
  }

  async function runStart() {
    const gen = ++runGenRef.current;
    const alive = () => gen === runGenRef.current;

    blackoutRef.current?.classList.add("active");
    await wait(300);
    if (!alive()) return;
    blackoutRef.current?.classList.remove("active");
    await wait(400);
    if (!alive()) return;

    curtainRef.current?.classList.add("open");
    await wait(1300);
    if (!alive()) return;

    stageRef.current?.classList.add("jury-visible");
    await wait(700);
    if (!alive()) return;

    stageRef.current?.classList.add("spotlight-on");
    await wait(500);
    if (!alive()) return;

    transcriptRef.current?.classList.add("visible");
    if (transcriptTextRef.current) {
      for (let i = 0; i <= OPENING_LINE.length; i++) {
        if (!alive()) return;
        transcriptTextRef.current.textContent = OPENING_LINE.slice(0, i);
        await wait(TYPEWRITER_MS);
      }
    }
    await wait(800);
    if (!alive()) return;

    if (skipBtnRef.current) {
      skipBtnRef.current.style.opacity = "0";
      skipBtnRef.current.style.pointerEvents = "none";
    }
    replayBtnRef.current?.classList.add("visible");
    finish();
  }

  function handleSkip() {
    runGenRef.current++; // in-flight chain'ler invalid
    applyFinalState();
    finish();
  }

  function handleReplay() {
    runGenRef.current++; // önceki run invalidate (yeni runStart kendi gen'ini alır)
    curtainRef.current?.classList.remove("open");
    stageRef.current?.classList.remove("jury-visible", "spotlight-on");
    transcriptRef.current?.classList.remove("visible");
    if (transcriptTextRef.current) transcriptTextRef.current.textContent = "";
    replayBtnRef.current?.classList.remove("visible");
    if (skipBtnRef.current) {
      skipBtnRef.current.style.opacity = "1";
      skipBtnRef.current.style.pointerEvents = "auto";
    }
    void runStart();
  }

  return (
    <div role="presentation" aria-label="Jüri simülasyonu açılış perdesi">
      <div ref={blackoutRef} className="sim-curtain-blackout" aria-hidden="true" />

      <div ref={stageRef} className="sim-curtain-stage" aria-hidden="true">
        <div className="sim-curtain-spotlight" />
        <div className="sim-curtain-lamp" />
        <div className="sim-curtain-floor-glow" />
        <div className="sim-curtain-table-bar" />

        <div className="sim-curtain-jury-row">
          <SeatStandard variant="left" />
          <SeatStandard variant="left2" />
          <SeatCenter />
          <SeatStandard variant="right2" />
          <SeatStandard variant="right" />
        </div>

        <div className="sim-curtain-floor" />
      </div>

      <div className="sim-curtain-rail" aria-hidden="true" />

      <div ref={curtainRef} className="sim-curtain-wrap" aria-hidden="true">
        <div className="sim-curtain-left" />
        <div className="sim-curtain-right" />
      </div>

      <div ref={transcriptRef} className="sim-curtain-transcript" aria-live="polite">
        <div className="sim-curtain-transcript-bubble">
          <div className="sim-curtain-who" aria-hidden="true">B</div>
          <div className="sim-curtain-tbody">
            <div className="sim-curtain-role">Jüri Başkanı · Açılış</div>
            <div className="sim-curtain-text">
              <span ref={transcriptTextRef} />
              <span className="sim-curtain-cursor" aria-hidden="true" />
            </div>
          </div>
        </div>
      </div>

      <button
        ref={skipBtnRef}
        type="button"
        className="sim-curtain-skip"
        onClick={handleSkip}
        aria-label="Simülasyonu atla"
      >
        <SkipIcon />
        Atla
      </button>

      <button
        ref={replayBtnRef}
        type="button"
        className="sim-curtain-replay"
        onClick={handleReplay}
        aria-label="Simülasyonu tekrar izle"
      >
        <ReplayIcon />
        Tekrar izle
      </button>
    </div>
  );
}

// ── SVG ikonlar — D17 satır 545, 550, 555 mirası ──

function SkipIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="12" height="12" aria-hidden="true">
      <polygon points="5 4 15 12 5 20 5 4" />
      <line x1="19" y1="5" x2="19" y2="19" />
    </svg>
  );
}

function ReplayIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="11" height="11" aria-hidden="true">
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 .49-3.75" />
    </svg>
  );
}

// ── Koltuk SVG'leri — D17 satır 423-517 mirası, kayıpsız port ──

interface SeatStandardProps {
  variant: "left" | "left2" | "right" | "right2";
}

function SeatStandard({ variant }: SeatStandardProps) {
  // Variant başına ufak fill farklılıkları (D17 satır 437/457/495/510)
  const seatFill =
    variant === "left" ? "#1a1210"
    : variant === "left2" ? "#1c1410"
    : variant === "right2" ? "#1a1410"
    : "#191410";

  // Silüet head-radius çeşitlemesi (D17 satır 426/454/492/507)
  const headR =
    variant === "left" ? 10
    : variant === "left2" ? 11
    : variant === "right2" ? 10
    : 9;

  return (
    <div className="sim-curtain-seat">
      <div className="sim-curtain-silhouette">
        <svg viewBox="0 0 56 90" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="28" cy="14" r={headR} fill="#1a1410" />
          <path
            d="M10 90 C10 55 18 42 28 38 C38 42 46 55 46 90Z"
            fill="#0f0c09"
          />
        </svg>
      </div>
      <svg width="110" height="160" viewBox="0 0 110 160" fill="none">
        <rect x="10" y="20" width="90" height="90" rx="6" fill={seatFill} stroke="rgba(255,200,100,0.06)" strokeWidth="1" />
        <rect x="8" y="108" width="94" height="18" rx="4" fill="#141008" />
        <rect x="18" y="126" width="10" height="34" rx="2" fill="#0f0d0a" />
        <rect x="82" y="126" width="10" height="34" rx="2" fill="#0f0d0a" />
        <rect x="4" y="70" width="10" height="52" rx="3" fill="#181410" />
        <rect x="96" y="70" width="10" height="52" rx="3" fill="#181410" />
      </svg>
    </div>
  );
}

function SeatCenter() {
  // Jüri başkanı — D17 satır 466-487
  return (
    <div className="sim-curtain-seat center">
      <div className="sim-curtain-silhouette" style={{ width: 64, height: 100 }}>
        <svg viewBox="0 0 64 100" fill="none">
          <circle cx="32" cy="15" r="12" fill="#1a1410" />
          <rect x="20" y="3" width="24" height="4" rx="1" fill="#1a1410" />
          <path d="M9 100 C9 58 19 44 32 40 C45 44 55 58 55 100Z" fill="#0f0c09" />
          <path d="M25 40 L32 55 L39 40" stroke="rgba(255,200,100,0.1)" strokeWidth="1.2" fill="none" />
        </svg>
      </div>
      <svg width="124" height="175" viewBox="0 0 124 175" fill="none">
        <rect x="10" y="18" width="104" height="105" rx="7" fill="#201816" stroke="rgba(255,200,100,0.1)" strokeWidth="1.5" />
        <path d="M12 18 Q62 10 112 18" stroke="rgba(255,200,100,0.08)" strokeWidth="1.5" fill="none" />
        <rect x="8" y="120" width="108" height="20" rx="5" fill="#181410" stroke="rgba(255,200,100,0.07)" strokeWidth="1" />
        <rect x="18" y="140" width="12" height="35" rx="2" fill="#100e0b" />
        <rect x="94" y="140" width="12" height="35" rx="2" fill="#100e0b" />
        <rect x="2" y="76" width="12" height="60" rx="3" fill="#1a1612" />
        <rect x="110" y="76" width="12" height="60" rx="3" fill="#1a1612" />
      </svg>
    </div>
  );
}
