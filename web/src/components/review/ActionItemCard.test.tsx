import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ActionItemCard } from "./ActionItemCard";
import type { ActionItem } from "@/lib/review-api";

const item: ActionItem = {
  action_id: "AI-001",
  priority: "P0",
  effort: "medium",
  expected_gain: "high",
  target_section: "Yöntem",
  instruction: "Güç analizi raporlayın.",
  acceptance_check: "Yöntem bölümünde güç analizi parametreleri var.",
  linked_finding_ids: ["F-001"],
};

describe("ActionItemCard", () => {
  it("öncelik, hedef bölüm, talimat ve kabul kontrolünü gösterir", () => {
    render(<ActionItemCard item={item} />);
    expect(screen.getByTestId("action-priority")).toHaveTextContent("P0");
    expect(screen.getByText("Yöntem")).toBeInTheDocument();
    expect(screen.getByText("Güç analizi raporlayın.")).toBeInTheDocument();
    expect(screen.getByText(/güç analizi parametreleri/)).toBeInTheDocument();
  });

  it("efor ve beklenen kazanç etiketli görünür", () => {
    render(<ActionItemCard item={item} />);
    expect(screen.getByText("Efor:")).toBeInTheDocument();
    expect(screen.getByText("Beklenen kazanç:")).toBeInTheDocument();
  });

  it("acceptance_check null ise kabul kutusu render edilmez", () => {
    render(<ActionItemCard item={{ ...item, acceptance_check: null }} />);
    expect(screen.queryByText(/Kabul kontrolü:/)).toBeNull();
  });
});
