import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ConfidenceMeter } from "./ConfidenceMeter";

describe("ConfidenceMeter", () => {
  it("sayısal yüzde gösterir (showNumeric varsayılan açık)", () => {
    render(<ConfidenceMeter value={0.72} />);
    expect(screen.getByTestId("confidence-numeric")).toHaveTextContent("%72");
  });

  it("niteliksel bant: yüksek/orta/düşük", () => {
    const { rerender } = render(<ConfidenceMeter value={0.9} />);
    expect(screen.getByText("Yüksek güven")).toBeInTheDocument();
    rerender(<ConfidenceMeter value={0.5} />);
    expect(screen.getByText("Orta güven")).toBeInTheDocument();
    rerender(<ConfidenceMeter value={0.1} />);
    expect(screen.getByText("Düşük güven")).toBeInTheDocument();
  });

  it("role=meter + aria-valuenow taşır", () => {
    render(<ConfidenceMeter value={0.42} label="Güven" />);
    const meter = screen.getByRole("meter");
    expect(meter).toHaveAttribute("aria-valuenow", "0.42");
    expect(meter).toHaveAttribute("aria-valuemin", "0");
    expect(meter).toHaveAttribute("aria-valuemax", "1");
  });

  it("showNumeric=false → sayısal gizli ama niteliksel kalır", () => {
    render(<ConfidenceMeter value={0.8} showNumeric={false} />);
    expect(screen.queryByTestId("confidence-numeric")).toBeNull();
    expect(screen.getByText("Yüksek güven")).toBeInTheDocument();
  });

  it("0..1 dışındaki değeri kırpar", () => {
    render(<ConfidenceMeter value={1.5} />);
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "1");
  });
});
