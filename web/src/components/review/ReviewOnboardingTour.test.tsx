// REVIEW_ONBOARDING_TURU_2026-08-17 — adım gezinme + tüm kapanış yollarının
// onClose'u çağırdığını doğrular (Atla/Escape/X/backdrop/son-adım "Anladım").

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

import { ReviewOnboardingTour } from "./ReviewOnboardingTour";

afterEach(() => cleanup());

describe("ReviewOnboardingTour", () => {
  it("adım 1'de başlar, 'Geri' butonu YOK, 'İleri' ile ilerler", () => {
    render(<ReviewOnboardingTour onClose={() => {}} />);
    const dialog = screen.getByTestId("review-onboarding-tour");
    expect(within(dialog).getByText("Adım 1 / 4")).toBeInTheDocument();
    expect(screen.queryByTestId("review-onboarding-tour-back")).toBeNull();

    fireEvent.click(screen.getByTestId("review-onboarding-tour-next"));
    expect(within(dialog).getByText("Adım 2 / 4")).toBeInTheDocument();
    expect(screen.getByTestId("review-onboarding-tour-back")).toBeInTheDocument();
  });

  it("'Geri' önceki adıma döner", () => {
    render(<ReviewOnboardingTour onClose={() => {}} />);
    fireEvent.click(screen.getByTestId("review-onboarding-tour-next"));
    fireEvent.click(screen.getByTestId("review-onboarding-tour-back"));
    expect(screen.getByText("Adım 1 / 4")).toBeInTheDocument();
  });

  it("son adımda buton 'Anladım' olur ve tıklanınca onClose çağrılır", () => {
    const onClose = vi.fn();
    render(<ReviewOnboardingTour onClose={onClose} />);
    const next = screen.getByTestId("review-onboarding-tour-next");
    fireEvent.click(next); // 1→2
    fireEvent.click(next); // 2→3
    fireEvent.click(next); // 3→4
    expect(screen.getByText("Adım 4 / 4")).toBeInTheDocument();
    expect(next).toHaveTextContent("Anladım");

    fireEvent.click(next);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("'Atla' onClose çağırır", () => {
    const onClose = vi.fn();
    render(<ReviewOnboardingTour onClose={onClose} />);
    fireEvent.click(screen.getByTestId("review-onboarding-tour-skip"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("X butonu onClose çağırır", () => {
    const onClose = vi.fn();
    render(<ReviewOnboardingTour onClose={onClose} />);
    fireEvent.click(screen.getByTestId("review-onboarding-tour-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("Escape onClose çağırır", () => {
    const onClose = vi.fn();
    render(<ReviewOnboardingTour onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("backdrop tıklaması onClose çağırır, diyalog içi tıklama ÇAĞIRMAZ", () => {
    const onClose = vi.fn();
    render(<ReviewOnboardingTour onClose={onClose} />);
    fireEvent.click(screen.getByTestId("review-onboarding-tour")); // backdrop
    expect(onClose).toHaveBeenCalledTimes(1);

    onClose.mockClear();
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).not.toHaveBeenCalled();
  });
});
