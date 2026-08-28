/**
 * Lansman kapısı (geçici, geri-alınabilir) — gerçek auth gelene kadar app
 * yüzeyini kapalı tutar. Omer kararı: "şimdilik sadece pazarlamayı canlıya al".
 *
 * Çalışma prensibi:
 *  - `LAUNCH_MODE=marketing` (runtime env, web servisinde set) → SADECE pazarlama
 *    rotaları açık; app/kokpit/admin rotaları `/`'e 307 (geçici) yönlenir.
 *  - Flag YOK / başka değer → kapı kapalı, tam app açık (dev + auth-sonrası canlı
 *    bu dosyaya dokunmadan, sadece env kaldırılarak normale döner).
 *
 * Neden middleware: tek noktadan tüm rotaları kapsar (global), her sayfaya tek tek
 * guard koymak yerine. Redirect 307 → kalıcı (308) DEĞİL: flag kalkınca tarayıcı/SEO
 * eski yönlendirmeyi cache'lemez.
 *
 * 2026-08-28: eski pazarlama sayfası `/landing`'den kök `/`'e taşındı (dashboard
 * yerine ana sayfa oldu). `/` artık PUBLIC_PATHS'te — DİKKAT: eğer `/` buraya
 * eklenmezse, LAUNCH_MODE=marketing iken `/landing`'in kendisi `/`'e yönlendiği
 * (bkz `(marketing)/landing/page.tsx` redirect stub) için sonsuz döngü oluşur
 * (`/`→middleware→`/landing`→sayfa→`/`→middleware→...). `/landing` hâlâ listede,
 * eski bookmark/link'ler kırılmasın diye (redirect stub'ına ulaşabilsin).
 *
 * Not: waitlist/API çağrıları cross-origin `NEXT_PUBLIC_API_URL`'e (api domain)
 * gider — same-origin /api rotası yok → bu kapı waitlist'i etkilemez.
 */
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// Lansman modunda herkese açık kalan pazarlama rotaları (tam eşleşme + alt-yollar).
const PUBLIC_PATHS = ["/", "/landing", "/ornek-rapor"] as const

export function middleware(req: NextRequest): NextResponse {
  // Kapı sadece LAUNCH_MODE=marketing iken devrede; aksi halde dokunma.
  if (process.env.LAUNCH_MODE !== "marketing") {
    return NextResponse.next()
  }

  const { pathname } = req.nextUrl
  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || (p !== "/" && pathname.startsWith(`${p}/`)),
  )
  if (isPublic) {
    return NextResponse.next()
  }

  // App/kokpit/admin yüzeyi lansmandan önce kapalı → ana sayfaya geçici yönlendir.
  const url = req.nextUrl.clone()
  url.pathname = "/"
  url.search = ""
  return NextResponse.redirect(url, 307)
}

export const config = {
  // _next iç dosyaları, statik varlıklar (uzantılı) ve favicon hariç tüm rotalar.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.[a-zA-Z0-9]+$).*)"],
}
