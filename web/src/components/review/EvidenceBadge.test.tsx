import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { EvidenceBadge } from "./EvidenceBadge";

describe("EvidenceBadge", () => {
  it("full_text_verified → doğrulama metni gösterir", () => {
    render(<EvidenceBadge supportLevel="full_text_verified" />);
    expect(screen.getByText("Tam metin doğrulandı")).toBeInTheDocument();
  });

  it("abstract_only, full_text_verified'tan görsel olarak AYRI (class + metin)", () => {
    const { container: verified } = render(<EvidenceBadge supportLevel="full_text_verified" />);
    const { container: abstract } = render(<EvidenceBadge supportLevel="abstract_only" />);
    const vCls = verified.querySelector('[data-testid="evidence-badge"]')?.className ?? "";
    const aCls = abstract.querySelector('[data-testid="evidence-badge"]')?.className ?? "";
    expect(vCls).toContain("arb-evidence-verified");
    expect(aCls).toContain("arb-evidence-abstract");
    expect(vCls).not.toEqual(aCls);
    expect(screen.getByText("Yalnızca özetten")).toBeInTheDocument();
  });

  it("unresolved, full_text_verified'tan görsel olarak AYRI (class + metin)", () => {
    const { container: unresolved } = render(<EvidenceBadge supportLevel="unresolved" />);
    const uCls = unresolved.querySelector('[data-testid="evidence-badge"]')?.className ?? "";
    expect(uCls).toContain("arb-evidence-unresolved");
    expect(screen.getByText("Doğrulanamadı")).toBeInTheDocument();
  });
});
