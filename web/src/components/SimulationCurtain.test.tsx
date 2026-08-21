import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render } from "@testing-library/react";

import { SimulationCurtain } from "./SimulationCurtain";

const setMatchMedia = (reduced: boolean) => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: reduced && query.includes("reduced-motion"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
};

beforeEach(() => {
  window.sessionStorage.clear();
  setMatchMedia(false);
});

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
});

describe("SimulationCurtain", () => {
  it("sessionStorage 'pm_simulation_seen'=1 → onComplete sync, animasyon başlamaz (.open yok)", () => {
    window.sessionStorage.setItem("pm_simulation_seen", "1");
    const onComplete = vi.fn();
    const { container } = render(<SimulationCurtain onComplete={onComplete} />);
    expect(onComplete).toHaveBeenCalledTimes(1);
    // Parent unmount edene kadar DOM render edilir; ama animasyon başlamaz → curtain kapalı kalır.
    expect(container.querySelector(".sim-curtain-wrap.open")).toBeNull();
    expect(container.querySelector(".sim-curtain-stage.jury-visible")).toBeNull();
  });

  it("prefers-reduced-motion → final state DOM (curtain.open + jury-visible + spotlight-on + transcript.visible)", () => {
    setMatchMedia(true);
    const onComplete = vi.fn();
    const { container } = render(<SimulationCurtain onComplete={onComplete} />);
    expect(onComplete).toHaveBeenCalled();
    expect(container.querySelector(".sim-curtain-wrap.open")).not.toBeNull();
    expect(container.querySelector(".sim-curtain-stage.jury-visible")).not.toBeNull();
    expect(container.querySelector(".sim-curtain-stage.spotlight-on")).not.toBeNull();
    expect(container.querySelector(".sim-curtain-transcript.visible")).not.toBeNull();
    expect(window.sessionStorage.getItem("pm_simulation_seen")).toBe("1");
  });

  it("Atla butonu → onComplete + sessionStorage set + final state uygulanır", () => {
    const onComplete = vi.fn();
    const { container, getByRole } = render(<SimulationCurtain onComplete={onComplete} />);
    act(() => {
      fireEvent.click(getByRole("button", { name: /Simülasyonu atla/i }));
    });
    expect(onComplete).toHaveBeenCalled();
    expect(window.sessionStorage.getItem("pm_simulation_seen")).toBe("1");
    expect(container.querySelector(".sim-curtain-wrap.open")).not.toBeNull();
    expect(container.querySelector(".sim-curtain-stage.jury-visible.spotlight-on")).not.toBeNull();
  });
});
