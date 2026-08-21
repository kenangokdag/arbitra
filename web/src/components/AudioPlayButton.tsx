// kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §2 KD-V1-S12-04
// V1-S12-03: Sesli dinlet butonu — ilk tıkta TTS fetch + blob cache,
// sonraki tıklarda cached blob'dan play/pause toggle (backend yeniden çağırılmaz).

"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Pause, Volume2 } from "lucide-react";

import { ApiError, fetchTTSReview, type TTSLang } from "@/lib/tts-api";

type Props = {
  text: string;
  lang?: TTSLang;
};

export function AudioPlayButton({ text, lang = "tr" }: Props) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Text/lang değişirse cached blob'u serbest bırak (yeni özet için yeniden fetch)
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  async function handleClick() {
    setError(null);

    // İlk tık: fetch et, blob URL oluştur, oynat
    if (!audioUrl) {
      setIsLoading(true);
      try {
        const blob = await fetchTTSReview({ content: text, lang });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        // Audio element render olunca ref bağlanır; useEffect ile play başlatırız
      } catch (e) {
        const msg =
          e instanceof ApiError && e.status === 429
            ? "Günlük dinlet kotanız doldu (yarın yenilenir)."
            : e instanceof Error
              ? e.message
              : "Ses üretilemedi.";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Cached: pause/play toggle
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      audio.play().catch(() => {
        // Browser autoplay policy bloklarsa sessiz geç — kullanıcı tekrar tıklar
      });
    } else {
      audio.pause();
    }
  }

  // audioUrl ilk set olunca otomatik oynat (kullanıcı tıkladı zaten — iOS auto-play kuralına uyar)
  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.play().catch(() => {
        // Auto-play bazen iOS'da hata; sessiz geç (kullanıcı tekrar tıklar)
      });
    }
  }, [audioUrl]);

  const label = isLoading
    ? "Hazırlanıyor…"
    : isPlaying
      ? "Durdur"
      : audioUrl
        ? "Devam et"
        : "Dinle";

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoading}
        data-testid="audio-play-button"
        aria-label={isPlaying ? "Sesi durdur" : "Özeti sesli dinle"}
        className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 font-sans text-[11.5px] text-stone-600 transition hover:border-stone-400 hover:text-stone-900 disabled:cursor-wait disabled:opacity-60"
        style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
      >
        {isLoading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : isPlaying ? (
          <Pause className="h-3.5 w-3.5" />
        ) : (
          <Volume2 className="h-3.5 w-3.5" />
        )}
        <span>{label}</span>
      </button>
      {audioUrl ? (
        <audio
          ref={audioRef}
          src={audioUrl}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          data-testid="audio-element"
          preload="auto"
        />
      ) : null}
      {error ? (
        <span
          data-testid="audio-error"
          className="font-crimson text-[11px] italic text-rose-600"
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}
