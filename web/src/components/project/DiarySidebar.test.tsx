// kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P005)
// 4 RTL test: empty / üç olay / pre-advisor mutation / filter değişimi.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

import { DiarySidebar } from "./DiarySidebar";
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

function fakeEvent(
  overrides: Partial<diaryApi.DiaryEventApi> = {},
): diaryApi.DiaryEventApi {
  return {
    id: "ev-1",
    projectId: "proj-1",
    userId: "user-1",
    pageSlug: "4.2_bosluk_profili",
    paperId: null,
    eventType: "kayit",
    payload: { note: "M5 boşluğunu işaretledim" },
    createdAt: "2026-05-08T10:00:00+00:00",
    resolvedAt: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("DiarySidebar", () => {
  it("boş timeline → 'Henüz kayıt yok' cümlesi gösterilir", async () => {
    vi.spyOn(diaryApi, "getDiaryTimeline").mockResolvedValue({
      items: [],
      nextCursor: null,
      count: 0,
    });

    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiarySidebar projectId="proj-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Henüz kayıt yok/i),
      ).toBeInTheDocument();
    });
  });

  it("üç olay → page_slug ve not metinleri render edilir", async () => {
    vi.spyOn(diaryApi, "getDiaryTimeline").mockResolvedValue({
      items: [
        fakeEvent({
          id: "e1",
          pageSlug: "4.2_bosluk_profili",
          payload: { note: "M5 boşluğu" },
        }),
        fakeEvent({
          id: "e2",
          pageSlug: "5.2_yayin_taslagi",
          eventType: "not",
          payload: { note: "RQ taslağı" },
          createdAt: "2026-05-09T14:00:00+00:00",
        }),
        fakeEvent({
          id: "e3",
          pageSlug: "6.1_yayin_icerigi_doldurma",
          eventType: "danismana_sor",
          payload: { note: "Doluluk %60" },
          createdAt: "2026-05-09T15:00:00+00:00",
        }),
      ],
      nextCursor: null,
      count: 3,
    });

    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiarySidebar projectId="proj-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getAllByTestId("diary-event-row")).toHaveLength(3);
    });
    expect(screen.getByText("4.2_bosluk_profili")).toBeInTheDocument();
    expect(screen.getByText("5.2_yayin_taslagi")).toBeInTheDocument();
    expect(screen.getByText("M5 boşluğu")).toBeInTheDocument();
    expect(screen.getByText("RQ taslağı")).toBeInTheDocument();
    expect(screen.getByText("Doluluk %60")).toBeInTheDocument();
  });

  it("'son 30 günü özetle' butonu → getPreAdvisorSummary çağrılır + özet render", async () => {
    vi.spyOn(diaryApi, "getDiaryTimeline").mockResolvedValue({
      items: [],
      nextCursor: null,
      count: 0,
    });
    const summarySpy = vi
      .spyOn(diaryApi, "getPreAdvisorSummary")
      .mockResolvedValue({
        summary: "Bu ay 4.2'de M5'i işaretledin.",
        eventCount: 1,
        periodStart: "2026-04-10T00:00:00+00:00",
        periodEnd: "2026-05-10T00:00:00+00:00",
      });

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiarySidebar projectId="proj-1" />
      </Wrapper>,
    );

    const btn = await screen.findByRole("button", {
      name: /son 30 günü özetle/i,
    });
    await user.click(btn);

    await waitFor(() => {
      expect(summarySpy).toHaveBeenCalledWith("proj-1");
    });
    expect(
      await screen.findByText(/Bu ay 4.2'de M5'i işaretledin/),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 olay/)).toBeInTheDocument();
  });

  it("'Çözüldü' butonu → patchDiaryEvent resolvedAt=now ile çağrılır", async () => {
    vi.spyOn(diaryApi, "getDiaryTimeline").mockResolvedValue({
      items: [
        fakeEvent({
          id: "ev-open",
          payload: { note: "açık olay" },
          resolvedAt: null,
        }),
      ],
      nextCursor: null,
      count: 1,
    });
    const patchSpy = vi
      .spyOn(diaryApi, "patchDiaryEvent")
      .mockResolvedValue(fakeEvent({ id: "ev-open", resolvedAt: "2026-05-11T11:00:00Z" }));

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiarySidebar projectId="proj-1" />
      </Wrapper>,
    );

    const btn = await screen.findByRole("button", { name: /^Çözüldü$/ });
    await user.click(btn);

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalled();
      const call = patchSpy.mock.calls[0]!;
      expect(call[0]).toBe("ev-open");
      expect(call[1].resolvedAt).toBeTruthy();
    });
  });

  it("'Geri aç' butonu → patchDiaryEvent resolvedAt=null ile çağrılır", async () => {
    vi.spyOn(diaryApi, "getDiaryTimeline").mockResolvedValue({
      items: [
        fakeEvent({
          id: "ev-done",
          payload: { note: "çözülmüş olay" },
          resolvedAt: "2026-05-09T10:00:00Z",
        }),
      ],
      nextCursor: null,
      count: 1,
    });
    const patchSpy = vi
      .spyOn(diaryApi, "patchDiaryEvent")
      .mockResolvedValue(fakeEvent({ id: "ev-done", resolvedAt: null }));

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiarySidebar projectId="proj-1" />
      </Wrapper>,
    );

    const btn = await screen.findByRole("button", { name: /^Geri aç$/ });
    await user.click(btn);

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalled();
      expect(patchSpy.mock.calls[0]![1].resolvedAt).toBeNull();
    });
  });

  it("'Düzenle' → textarea + Kaydet → patchDiaryEvent payload.note guncel", async () => {
    vi.spyOn(diaryApi, "getDiaryTimeline").mockResolvedValue({
      items: [
        fakeEvent({
          id: "ev-edit",
          payload: { note: "eski not" },
          resolvedAt: null,
        }),
      ],
      nextCursor: null,
      count: 1,
    });
    const patchSpy = vi
      .spyOn(diaryApi, "patchDiaryEvent")
      .mockResolvedValue(fakeEvent({ id: "ev-edit", payload: { note: "yeni not" } }));

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiarySidebar projectId="proj-1" />
      </Wrapper>,
    );

    await user.click(await screen.findByRole("button", { name: /^Düzenle$/ }));
    const textarea = screen.getByLabelText(/not düzenle/i);
    await act(async () => {
      await user.clear(textarea);
      await user.type(textarea, "yeni not");
    });
    await user.click(screen.getByRole("button", { name: /^Kaydet$/ }));

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalled();
      const call = patchSpy.mock.calls[0]!;
      expect(call[0]).toBe("ev-edit");
      expect((call[1].payload as { note?: string }).note).toBe("yeni not");
    });
  });

  it("page_slug filter input → getDiaryTimeline yeni filter ile çağrılır", async () => {
    const spy = vi
      .spyOn(diaryApi, "getDiaryTimeline")
      .mockResolvedValue({ items: [], nextCursor: null, count: 0 });

    const user = userEvent.setup();
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <DiarySidebar projectId="proj-1" />
      </Wrapper>,
    );

    await waitFor(() => expect(spy).toHaveBeenCalled());

    const input = screen.getByLabelText(/sayfa filtresi/i);
    await act(async () => {
      await user.type(input, "5.2");
    });

    await waitFor(() => {
      const lastCall = spy.mock.calls.at(-1);
      expect(lastCall?.[0]).toMatchObject({
        projectId: "proj-1",
        pageSlug: "5.2",
      });
    });
  });
});
