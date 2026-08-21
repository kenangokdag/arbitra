// kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §2 KD-V1-S12-01
// V1-S12-02: Web Speech API hook — sesli arama girişi.
// Tarayıcı native (Chrome/Edge/Safari iOS 14.5+); Firefox eski sürüm desteklemez
// → isSupported=false, buton gizlenir.

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// SpeechRecognition global type (Webkit prefix dahil — runtime fallback)
type SpeechRecognitionEvent = {
  results: { 0: { transcript: string }; isFinal: boolean }[] & {
    length: number;
    item: (i: number) => { 0: { transcript: string }; isFinal: boolean };
  };
};

type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export type UseSpeechInputOptions = {
  lang?: string;
  onResult: (transcript: string) => void;
  onError?: (error: string) => void;
};

export type UseSpeechInputReturn = {
  isSupported: boolean;
  isListening: boolean;
  start: () => void;
  stop: () => void;
};

export function useSpeechInput(
  opts: UseSpeechInputOptions,
): UseSpeechInputReturn {
  const { lang = "tr-TR", onResult, onError } = opts;
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const recRef = useRef<SpeechRecognitionInstance | null>(null);

  // Mount sonrası SSR-safe support tespiti
  useEffect(() => {
    setIsSupported(getSpeechRecognitionCtor() !== null);
  }, []);

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return;
    if (recRef.current) {
      // Halihazırda dinliyor; tekrar start çağırmak hata fırlatır
      return;
    }
    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const first = e.results[0];
      if (first?.isFinal) {
        onResult(first[0].transcript.trim());
      }
    };
    rec.onerror = (e: { error: string }) => {
      onError?.(e.error);
      setIsListening(false);
      recRef.current = null;
    };
    rec.onend = () => {
      setIsListening(false);
      recRef.current = null;
    };
    recRef.current = rec;
    setIsListening(true);
    rec.start();
  }, [lang, onResult, onError]);

  const stop = useCallback(() => {
    recRef.current?.stop();
  }, []);

  return { isSupported, isListening, start, stop };
}
