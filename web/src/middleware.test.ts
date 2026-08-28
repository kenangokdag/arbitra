/**
 * Lansman kapısı (middleware) davranış kilidi.
 * - Flag YOK → her rota geçer (app açık).
 * - LAUNCH_MODE=marketing → sadece / + /landing + /ornek-rapor geçer; app/admin → 307 /.
 * 2026-08-28: eski pazarlama sayfası /landing'den köke (/) taşındı — / artık
 * public (kanıt: dashboard yerine ana sayfa oldu, /landing sadece redirect stub'ı).
 */
import { NextRequest } from "next/server"
import { afterEach, describe, expect, it } from "vitest"

import { middleware } from "./middleware"

function req(path: string): NextRequest {
  return new NextRequest(new URL(`https://web.arbitra.app${path}`))
}

const APP_PATHS = [
  "/chat",
  "/review",
  "/review/abc123",
  "/project/p1/x",
  "/settings",
  "/admin",
  "/q",
  "/demo", // pazarlama grubunda ama lansman kapsamı dışı → kapalı
]

const PUBLIC = ["/", "/landing", "/ornek-rapor", "/ornek-rapor/anything"]

afterEach(() => {
  delete process.env.LAUNCH_MODE
})

describe("middleware — lansman kapısı", () => {
  it("flag yokken hiçbir rotaya dokunmaz (app açık)", () => {
    delete process.env.LAUNCH_MODE
    for (const p of [...APP_PATHS, ...PUBLIC]) {
      const res = middleware(req(p))
      // next() → redirect değil (location header yok)
      expect(res.headers.get("location"), `pass beklenir: ${p}`).toBeNull()
    }
  })

  it("LAUNCH_MODE=marketing iken app/admin rotaları /'e 307", () => {
    process.env.LAUNCH_MODE = "marketing"
    for (const p of APP_PATHS) {
      const res = middleware(req(p))
      expect(res.status, `307 beklenir: ${p}`).toBe(307)
      expect(new URL(res.headers.get("location")!).pathname).toBe("/")
    }
  })

  it("LAUNCH_MODE=marketing iken pazarlama rotaları açık kalır", () => {
    process.env.LAUNCH_MODE = "marketing"
    for (const p of PUBLIC) {
      const res = middleware(req(p))
      expect(res.headers.get("location"), `pass beklenir: ${p}`).toBeNull()
    }
  })
})
