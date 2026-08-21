"use client";

// FAZ 4B — global tema uygulayıcı. Mount'ta useTheme() ile temayı okur ve
// document.documentElement üzerine uygular (applyTheme). HATA / loading / veri-yok
// → HİÇBİR setProperty çağrılmaz → globals.css varsayılanları kalır (uygulama ASLA
// kırılmaz, FOUC minimal çünkü seed = mevcut globals.css değerleri). Görünür DOM
// üretmez; sadece children'ı geçirir.

import { useEffect } from "react";

import { useTheme } from "@/hooks/useReview";
import { applyTheme } from "@/lib/theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { data } = useTheme();

  useEffect(() => {
    if (!data) return; // loading / error / yok → varsayılan korunur
    if (typeof document === "undefined") return;
    applyTheme(document.documentElement, data);
  }, [data]);

  return <>{children}</>;
}
