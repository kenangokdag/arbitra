import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { DegradedNotice } from "./DegradedNotice";

describe("DegradedNotice", () => {
  it("sınırlama nedenini görünür biçimde gösterir", () => {
    render(<DegradedNotice reason="Tam metin erişimi yoktu; yalnızca özetten değerlendirildi." />);
    expect(screen.getByText("Sınırlı sonuç")).toBeInTheDocument();
    expect(
      screen.getByText("Tam metin erişimi yoktu; yalnızca özetten değerlendirildi."),
    ).toBeInTheDocument();
  });

  it("role=status ile ekran-okuyucuya duyurulur", () => {
    render(<DegradedNotice reason="x" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
