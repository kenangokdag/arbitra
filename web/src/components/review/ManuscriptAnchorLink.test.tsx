import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { ManuscriptAnchorLink } from "./ManuscriptAnchorLink";
import type { ManuscriptAnchor } from "@/lib/review-api";

const anchor: ManuscriptAnchor = {
  anchor_id: "A-001",
  section: "Yöntem",
  quote: "Toplam 84 katılımcı çalışmaya dahil edildi.",
};

describe("ManuscriptAnchorLink", () => {
  it("erişilebilir adı bölüm + alıntıyı içerir", () => {
    render(<ManuscriptAnchorLink anchor={anchor} />);
    const btn = screen.getByRole("button");
    expect(btn).toHaveAccessibleName(/Yöntem/);
    expect(btn).toHaveAccessibleName(/84 katılımcı/);
  });

  it("tıklanınca onOpen çağrılır", () => {
    const onOpen = vi.fn();
    render(<ManuscriptAnchorLink anchor={anchor} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("section/quote null ise yine erişilebilir ad üretir", () => {
    render(
      <ManuscriptAnchorLink anchor={{ anchor_id: "A-x", section: null, quote: null }} />,
    );
    expect(screen.getByRole("button")).toHaveAccessibleName(/Makale/);
  });
});
