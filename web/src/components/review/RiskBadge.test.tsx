import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RiskBadge } from "./RiskBadge";

describe("RiskBadge", () => {
  it("her zaman metin etiketi render eder (renk tek sinyal değil)", () => {
    render(<RiskBadge severity="critical" />);
    expect(screen.getByText("Kritik")).toBeInTheDocument();
  });

  it("severity → ayırt edici semantik class verir", () => {
    const { container } = render(<RiskBadge severity="major" />);
    const badge = container.querySelector('[data-testid="risk-badge"]');
    expect(badge?.className).toContain("arb-risk-major");
    expect(badge?.getAttribute("data-severity")).toBe("major");
  });

  it("farklı severity → farklı class (critical ≠ minor)", () => {
    const { container: c1 } = render(<RiskBadge severity="critical" />);
    const { container: c2 } = render(<RiskBadge severity="minor" />);
    const cls1 = c1.querySelector('[data-testid="risk-badge"]')?.className ?? "";
    const cls2 = c2.querySelector('[data-testid="risk-badge"]')?.className ?? "";
    expect(cls1).not.toEqual(cls2);
  });

  it("priority verilince P0/P1/P2 metni gösterir", () => {
    render(<RiskBadge severity="major" priority="P0" />);
    expect(screen.getByText("P0")).toBeInTheDocument();
  });

  it("özel label override eder", () => {
    render(<RiskBadge severity="info" label="Özel etiket" />);
    expect(screen.getByText("Özel etiket")).toBeInTheDocument();
  });
});
