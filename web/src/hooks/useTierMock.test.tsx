import { describe, it, expect, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

import { useTierMock } from "./useTierMock";

describe("useTierMock", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("default = anon, isAuthenticated false", () => {
    const { result } = renderHook(() => useTierMock());
    expect(result.current.tier).toBe("anon");
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("ogrenci storage → tier=ogrenci, authenticated", () => {
    window.localStorage.setItem("arbitra_tier_mock", "ogrenci");
    const { result } = renderHook(() => useTierMock());
    expect(result.current.tier).toBe("ogrenci");
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("arastirmaci storage → tier=arastirmaci", () => {
    window.localStorage.setItem("arbitra_tier_mock", "arastirmaci");
    const { result } = renderHook(() => useTierMock());
    expect(result.current.tier).toBe("arastirmaci");
  });

  it("profesyonel storage → tier=profesyonel", () => {
    window.localStorage.setItem("arbitra_tier_mock", "profesyonel");
    const { result } = renderHook(() => useTierMock());
    expect(result.current.tier).toBe("profesyonel");
  });

  it("invalid storage value → fallback anon", () => {
    window.localStorage.setItem("arbitra_tier_mock", "T1+");
    const { result } = renderHook(() => useTierMock());
    expect(result.current.tier).toBe("anon");
  });
});
