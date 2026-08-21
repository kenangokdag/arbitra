// kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P006)
// 3 RTL test: kayit / danismana_sor / kutuphane_ekle event_type doğrulaması.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

import { DiaryActions } from "./DiaryActions";
import * as diaryApi from "@/lib/diary-api";

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function fakeEventResponse(
  overrides: Partial<diaryApi.DiaryEventApi> = {},
): diaryApi.DiaryEventApi {
  return {
    id: "ev-1",
    projectId: "proj-1",
    userId: "user-1",
    pageSlug: "4.2_bosluk_profili",
    paperId: null,
    eventType: "kayit",
    payload: {},
    createdAt: "2026-05-10T10:00:00+00:00",
    resolvedAt: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("DiaryActions", () => {
  it("'Ajandama Kaydet' tıklanınca createDiaryEvent kayit ile çağrılır", async () => {
    const spy = vi
      .spyOn(diaryApi, "createDiaryEvent")
      .mockResolvedValue(fakeEventResponse({ eventType: "kayit" }));

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiaryActions projectId="proj-1" pageSlug="4.2_bosluk_profili" />
      </Wrapper>,
    );

    await user.click(screen.getByRole("button", { name: /Ajandama Kaydet/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: "proj-1",
          pageSlug: "4.2_bosluk_profili",
          eventType: "kayit",
          paperId: null,
          payload: {},
        }),
      );
    });
  });

  it("not yazılıp 'Danışmana Sor' tıklanınca payload.note ve danismana_sor gider", async () => {
    const spy = vi
      .spyOn(diaryApi, "createDiaryEvent")
      .mockResolvedValue(
        fakeEventResponse({
          eventType: "danismana_sor",
          payload: { note: "M5 boşluğu" },
        }),
      );

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiaryActions projectId="proj-1" pageSlug="4.2_bosluk_profili" />
      </Wrapper>,
    );

    const textarea = screen.getByLabelText(/Defter notu/i);
    await user.type(textarea, "M5 boşluğu");
    await user.click(screen.getByRole("button", { name: /Danışmana Sor/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: "danismana_sor",
          payload: { note: "M5 boşluğu" },
        }),
      );
    });
  });

  it("paperId verildiğinde 'Kütüphaneme Ekle' kutuphane_ekle + paperId ile çağrılır", async () => {
    const spy = vi
      .spyOn(diaryApi, "createDiaryEvent")
      .mockResolvedValue(
        fakeEventResponse({ eventType: "kutuphane_ekle", paperId: "paper-42" }),
      );

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiaryActions
          projectId="proj-1"
          pageSlug="4.2_bosluk_profili"
          paperId="paper-42"
        />
      </Wrapper>,
    );

    await user.click(screen.getByRole("button", { name: /Kütüphaneme Ekle/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: "kutuphane_ekle",
          paperId: "paper-42",
        }),
      );
    });
  });
});
