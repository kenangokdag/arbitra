import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";

import { PenIcon } from "./pen";

describe("PenIcon", () => {
  it("D16 birebir 3 path geometri (path × 2 + line)", () => {
    const { container } = render(<PenIcon />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg?.querySelectorAll("path")).toHaveLength(2);
    expect(svg?.querySelectorAll("line")).toHaveLength(1);
    expect(svg?.getAttribute("viewBox")).toBe("0 0 24 24");
    expect(svg?.getAttribute("stroke")).toBe("currentColor");
  });

  it("aria-hidden default + props inherit (className + width override)", () => {
    const { container } = render(<PenIcon className="size-5" width={20} />);
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
    expect(svg).toHaveClass("size-5");
    expect(svg?.getAttribute("width")).toBe("20");
  });
});
