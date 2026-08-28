"use client";

/* 2026-08-28: /landing içeriği kök `/`'e taşındı (Ömer kararı — dashboard
 * yerine pazarlama sayfası ana sayfa oldu). Bu dosya sadece eski
 * bookmark/link'ler kırılmasın diye kalıyor — kalıcı olarak / 'e yönlendirir. */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LandingRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);
  return null;
}
