/**
 * Dev JWT mock — Sercan magic-link SMTP gelene kadar (KD-21+, F5).
 * Production'da next-auth + Supabase Auth swap edilecek.
 *
 * 2026-08-28 (P0, danışman pilotu öncesi): önceden TÜM tarayıcılar aynı
 * sabit DEV_USER_SUB ile geliyordu — herkes sistemde TEK bir "kullanıcı"
 * gibi görünüyordu, projeler/geçmiş işler karışıyordu. Artık her tarayıcı
 * ilk ziyarette crypto.randomUUID() ile kendi kalıcı kimliğini üretip
 * localStorage'a kaydediyor (getOrCreateUserId) — farklı danışmanlar
 * (farklı tarayıcı/cihaz) birbirinden ayrışıyor, aynı tarayıcı hep aynı
 * kimlikte kalıyor. Backend değişikliği GEREKMEDİ — DEMO_AUTH_BYPASS
 * (api/middleware/auth.py) sub claim'ini generic okuyor, belirli bir
 * değere bağlı değil.
 * STORAGE_KEY v3→v4: eski sabit-sub token cache'ini GEÇERSİZ kılmak için
 * kasıtlı versiyon atlaması — v3'te zaten var olan tarayıcılar da bu
 * değişiklikten sonra yeni, kendi rastgele kimliğiyle token üretir (eski
 * paylaşılan sub'a bağlı proje verisi UI'dan artık erişilemez olur, DB'de
 * SİLİNMEZ — bilerek, çünkü o veri hep paylaşılan/test amaçlıydı).
 */

const STORAGE_KEY = "arbitra.dev_token_v4";
const USER_ID_KEY = "arbitra.dev_user_id_v1";

function getOrCreateUserId(): string {
  if (typeof window === "undefined") {
    // SSR/derleme zamanı — gerçek bir kullanıcı isteği değil, sabit placeholder yeterli.
    return "00000000-0000-0000-0000-000000000000";
  }
  let id = window.localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

function base64UrlEncode(input: string): string {
  if (typeof window === "undefined") {
    return Buffer.from(input).toString("base64url");
  }
  return btoa(input).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function buildDevToken(sub: string = getOrCreateUserId()): string {
  const header = { alg: "HS256", typ: "JWT" };
  const payload = {
    sub,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24,
  };
  const signature = "dev-mock-signature";
  return [
    base64UrlEncode(JSON.stringify(header)),
    base64UrlEncode(JSON.stringify(payload)),
    signature,
  ].join(".");
}

export function getToken(): string {
  if (typeof window === "undefined") return buildDevToken();
  let token = window.localStorage.getItem(STORAGE_KEY);
  if (!token) {
    token = buildDevToken();
    window.localStorage.setItem(STORAGE_KEY, token);
  }
  return token;
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
  window.localStorage.removeItem(USER_ID_KEY);
}
