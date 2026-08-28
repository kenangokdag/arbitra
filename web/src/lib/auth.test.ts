// 2026-08-28 (P0, danışman pilotu öncesi) — önceden TÜM tarayıcılar sabit
// DEV_USER_SUB ile geliyordu (herkes tek "kullanıcı"). Artık her tarayıcı
// kendi rastgele kalıcı kimliğini üretiyor (getOrCreateUserId). Bu testler:
// (1) aynı tarayıcı (localStorage) hep AYNI kimlikte kalır, (2) farklı
// tarayıcılar (ayrı localStorage) FARKLI kimlik üretir. Backend-taraflı
// izolasyon (user_id filtreleme, RLS) bu değişiklikle ilgisiz — zaten var
// olan, ayrı test edilen bir mekanizma (bkz db/migrations/0041_review_domain.sql
// RLS policy user_id = auth.jwt()->>'sub').

import { beforeEach, describe, expect, it } from "vitest";

import { buildDevToken, clearToken, getToken } from "./auth";

function decodePayload(token: string): { sub: string; iat: number; exp: number } {
  const [, payloadB64] = token.split(".");
  const json = Buffer.from(payloadB64!, "base64url").toString("utf-8");
  return JSON.parse(json);
}

beforeEach(() => {
  globalThis.localStorage?.clear?.();
});

describe("getToken — kalıcı, tarayıcıya-özel kimlik", () => {
  it("aynı tarayıcı (localStorage) her çağrıda AYNI sub'ı üretir", () => {
    const t1 = getToken();
    const t2 = getToken();
    const s1 = decodePayload(t1).sub;
    const s2 = decodePayload(t2).sub;
    expect(s1).toBe(s2);
  });

  it("localStorage temizlenmeden tekrar tekrar çağrılınca token değişmez (cache)", () => {
    expect(getToken()).toBe(getToken());
  });

  it("farklı 'tarayıcılar' (ayrı localStorage state) FARKLI sub üretir", () => {
    const tokenA = getToken();
    const subA = decodePayload(tokenA).sub;

    globalThis.localStorage.clear(); // yeni "tarayıcı" simülasyonu

    const tokenB = getToken();
    const subB = decodePayload(tokenB).sub;

    expect(subA).not.toBe(subB);
  });

  it("sub geçerli bir UUID formatında (crypto.randomUUID)", () => {
    const sub = decodePayload(getToken()).sub;
    expect(sub).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });

  it("clearToken() sonrası YENİ bir kimlik üretilir (hesap silme senaryosu)", () => {
    const before = decodePayload(getToken()).sub;
    clearToken();
    const after = decodePayload(getToken()).sub;
    expect(before).not.toBe(after);
  });
});

describe("buildDevToken — explicit sub geçilirse öncelik onda", () => {
  it("explicit sub verilirse localStorage'daki kimlik yok sayılır", () => {
    const token = buildDevToken("explicit-test-sub");
    expect(decodePayload(token).sub).toBe("explicit-test-sub");
  });
});
