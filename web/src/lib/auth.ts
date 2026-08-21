/**
 * Dev JWT mock — Sercan magic-link SMTP gelene kadar (KD-21+, F5).
 * Production'da next-auth + Supabase Auth swap edilecek.
 */

const STORAGE_KEY = "arbitra.dev_token_v3";
const DEV_USER_SUB = "9c7d34fc-806c-4854-a2e6-85dfde1a76c0";

function base64UrlEncode(input: string): string {
  if (typeof window === "undefined") {
    return Buffer.from(input).toString("base64url");
  }
  return btoa(input).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function buildDevToken(sub: string = DEV_USER_SUB): string {
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
}
