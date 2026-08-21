import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { ChatThreadMessage } from "@/stores/ui";

import { ChatThread } from "./ChatThread";

const baseTime = new Date("2026-05-01T10:00:00Z").getTime();

const msg = (
  role: ChatThreadMessage["role"],
  content: string,
  offsetMs = 0
): ChatThreadMessage => ({
  id: `m-${Math.random().toString(36).slice(2, 9)}`,
  role,
  content,
  timestamp: baseTime + offsetMs,
});

afterEach(cleanup);

describe("ChatThread", () => {
  it("3 mesaj render — adviser + user bubble + role=log + aria-live polite", () => {
    const messages = [
      msg("user", "Merhaba"),
      msg("assistant", "Selam, nasıl yardımcı olabilirim?", 1000),
      msg("user", "Bu konuyu daraltır mısın?", 2000),
    ];
    render(<ChatThread messages={messages} onSend={vi.fn()} />);
    const log = screen.getByRole("log");
    expect(log).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText("Merhaba")).toBeDefined();
    expect(screen.getByText("Selam, nasıl yardımcı olabilirim?")).toBeDefined();
    expect(screen.getByText("Bu konuyu daraltır mısın?")).toBeDefined();
  });

  it("isPending → typing indicator role=status + aria-label 'Danışman yazıyor'", () => {
    render(<ChatThread messages={[]} onSend={vi.fn()} isPending />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Danışman yazıyor");
  });

  it("suggestions render edilir + click handleSend ile onSend çağrılır", () => {
    const onSend = vi.fn();
    render(
      <ChatThread
        messages={[]}
        onSend={onSend}
        suggestions={["Bu konuyu daralt", "Hangi yöntem", "Niye dahil"]}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Bu konuyu daralt" }));
    expect(onSend).toHaveBeenCalledWith("Bu konuyu daralt");
  });

  it("textarea Enter (no shift) → handleSend; Shift+Enter → newline (handleSend yok)", () => {
    const onSend = vi.fn();
    render(<ChatThread messages={[]} onSend={onSend} />);
    const textarea = screen.getByLabelText("Danışmana mesaj yaz");
    fireEvent.change(textarea, { target: { value: "Test mesaj" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSend).toHaveBeenCalledWith("Test mesaj");

    onSend.mockClear();
    fireEvent.change(textarea, { target: { value: "Çok satırlı" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("emptyState render edilir mesaj yok + isPending false ise", () => {
    render(
      <ChatThread
        messages={[]}
        onSend={vi.fn()}
        emptyState={<p>Henüz mesaj yok</p>}
      />
    );
    expect(screen.getByText("Henüz mesaj yok")).toBeDefined();
  });

  it("errorMessage role=alert ile gösterilir", () => {
    render(
      <ChatThread
        messages={[msg("user", "deneme")]}
        onSend={vi.fn()}
        errorMessage="Sunucu hatası"
      />
    );
    expect(screen.getByRole("alert").textContent).toBe("Sunucu hatası");
  });
});
