import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SearchPending } from "./SearchPending";

describe("SearchPending", () => {
  it("ARIA role=status + aria-live=polite + aria-label görünür", () => {
    render(<SearchPending />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveAttribute(
      "aria-label",
      "Sizin için akademik makaleler aranıyor"
    );
  });

  it("Özel label override edilebilir", () => {
    render(<SearchPending label="Tarama yapılıyor" />);
    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "Tarama yapılıyor"
    );
  });

  it("Görünür alt başlık Lora italic ekol — label '…' ile birleşir", () => {
    render(<SearchPending />);
    expect(
      screen.getByText(/Sizin için akademik makaleler aranıyor…/)
    ).toBeInTheDocument();
  });

  it("3D carousel motion-safe varyant render edilir", () => {
    const { container } = render(<SearchPending />);
    const carousel = container.querySelector(
      '[data-testid="searchpending-carousel"]'
    );
    expect(carousel).toBeInTheDocument();
    expect(carousel?.className).toContain("motion-reduce:hidden");
  });

  it("3D carousel 6 kart içerir (decision_band semantic strip rotation)", () => {
    const { container } = render(<SearchPending />);
    const carousel = container.querySelector(
      '[data-testid="searchpending-carousel"]'
    );
    const cards = carousel?.querySelectorAll("article");
    expect(cards?.length).toBe(6);
  });

  it("prefers-reduced-motion fallback 3 statik skeleton içerir", () => {
    const { container } = render(<SearchPending />);
    const fallback = container.querySelector(
      '[data-testid="searchpending-static"]'
    );
    expect(fallback).toBeInTheDocument();
    expect(fallback?.className).toContain("motion-reduce:flex");
    expect(fallback?.className).toContain("hidden");
    // 3 skeleton card
    const cards = fallback?.querySelectorAll(".rounded-\\[14px\\]");
    expect(cards?.length).toBe(3);
  });

  it("Decision_band semantic strip 4 farklı renk: stripe-ok/info/accent/warn (custom utility — Tailwind v4 directional border-color generate etmiyor)", () => {
    const { container } = render(<SearchPending />);
    const carousel = container.querySelector(
      '[data-testid="searchpending-carousel"]'
    );
    const html = carousel?.innerHTML ?? "";
    expect(html).toContain("stripe-ok");
    expect(html).toContain("stripe-info");
    expect(html).toContain("stripe-accent");
    expect(html).toContain("stripe-warn");
  });

  it("anim-searchpending custom utility class kullanılır (Tailwind v4 [animation:...] arbitrary parse etmiyor)", () => {
    const { container } = render(<SearchPending />);
    const animatedLayer = container.querySelector(".anim-searchpending");
    expect(animatedLayer).toBeInTheDocument();
  });
});
