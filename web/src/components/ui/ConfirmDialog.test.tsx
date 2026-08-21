// ConfirmDialog — typed-confirmation gate + çift-gönderim kilidi + okunur hata.
// Yıkıcı eylemin can damarı: kullanıcı metni BİREBİR yazana kadar onay PASİF;
// hata ham JSON değil okunur Türkçe; ApiError 404 → anlamlı mesaj.

import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ConfirmDialog } from "./ConfirmDialog";
import { ApiError } from "@/lib/api";

afterEach(() => vi.restoreAllMocks());

function baseProps() {
  return {
    open: true,
    onClose: vi.fn(),
    title: "Sil",
    description: "Geri alınamaz.",
    confirmLabel: "Sil",
  };
}

describe("ConfirmDialog — typed-confirmation gate", () => {
  it("metin tam eşleşene kadar onay butonu pasif, eşleşince aktif", () => {
    render(
      <ConfirmDialog
        {...baseProps()}
        confirmPhrase="HESABIMI SİL"
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    const confirmBtn = screen.getByRole("button", { name: "Sil" });
    expect(confirmBtn).toBeDisabled();

    const input = screen.getByLabelText("Onay metni: HESABIMI SİL");
    fireEvent.change(input, { target: { value: "HESABIMI" } }); // kısmi
    expect(confirmBtn).toBeDisabled();

    fireEvent.change(input, { target: { value: "HESABIMI SİL" } }); // tam
    expect(confirmBtn).toBeEnabled();
  });

  it("onay → onConfirm çağrılır, başarı görünümü + onSuccess", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onSuccess = vi.fn();
    render(
      <ConfirmDialog
        {...baseProps()}
        confirmPhrase="SİL"
        onConfirm={onConfirm}
        onSuccess={onSuccess}
        success={{ title: "Silindi", description: "bitti" }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Onay metni: SİL"), {
      target: { value: "SİL" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sil" }));

    // başarı görünümü görünür
    expect(await screen.findByText("Silindi")).toBeInTheDocument();
    expect(onConfirm).toHaveBeenCalledTimes(1);
    // kısa bekleme sonrası onSuccess (yönlendirme) tetiklenir
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1), {
      timeout: 2000,
    });
  });

  it("ApiError 404 → ham JSON değil okunur Türkçe mesaj gösterir", async () => {
    const onConfirm = vi
      .fn()
      .mockRejectedValue(new ApiError(404, { detail: "not found" }, "API 404"));
    render(<ConfirmDialog {...baseProps()} onConfirm={onConfirm} />);

    fireEvent.click(screen.getByRole("button", { name: "Sil" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Kayıt bulunamadı"),
    );
    // ham JSON sızmamalı
    expect(screen.queryByText(/API 404/)).toBeNull();
  });
});
