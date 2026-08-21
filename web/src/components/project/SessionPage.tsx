"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";

interface Message {
  id: number;
  role: "advisor" | "user";
  text: string;
  ref?: string;
}

const mockMessages: Message[] = [
  {
    id: 1,
    role: "advisor",
    text: "Merhaba! Bugun ne uzerinde calismak istiyorsun?",
  },
  {
    id: 2,
    role: "user",
    text: "MCDM konusundaki bosluk analizimi gozden gecirmek istiyorum.",
  },
  {
    id: 3,
    role: "advisor",
    text: "Bosluk haritanda 3 hucre one cikiyor: supplier selection + hesitant fuzzy, sustainability + BWM, ve bibliometric + co-citation. Hangisiyle baslamak istersin?",
    ref: "1",
  },
  {
    id: 4,
    role: "user",
    text: "Supplier selection + hesitant fuzzy ilginc gorunuyor. Mevcut literaturde ne kadar calisma var?",
  },
  {
    id: 5,
    role: "advisor",
    text: "2020-2025 arasinda 47 calisma buldum. Cogu TOPSIS veya VIKOR kullanmis. Hesitant fuzzy + BWM kombinasyonu hemen hemen bos — sadece 3 calisma var ve hicbiri supplier selection baglaminda degil.",
    ref: "2",
  },
];

export function SessionPage() {
  const [inputValue, setInputValue] = useState("");

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Ofis saatindeyiz. Ne konusmak istersen, acik acik sorabilirsin." />

      <div className="flex gap-6">
        {/* Chat area */}
        <div className="mx-auto flex max-w-3xl flex-1 flex-col">
          <div className="flex-1 rounded-2xl border border-stone-200 bg-white shadow-sm">
            {/* Messages */}
            <div className="space-y-4 p-6">
              {mockMessages.map((msg) =>
                msg.role === "advisor" ? (
                  <div key={msg.id} className="flex items-start gap-3">
                    {/* Avatar */}
                    <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full ring-2 ring-[#C9A961] bg-amber-50">
                      <span className="text-xs font-bold text-[#C9A961]">
                        D
                      </span>
                    </div>
                    <div
                      className="max-w-[80%] rounded-2xl rounded-tl-sm px-4 py-3"
                      style={{ backgroundColor: "#FCEBD9" }}
                    >
                      <p className="font-display text-sm italic leading-relaxed text-stone-700">
                        {msg.text}
                        {msg.ref && (
                          <span className="ml-1 inline-block rounded bg-amber-200/60 px-1.5 py-0.5 text-xs font-semibold not-italic text-amber-800">
                            [{msg.ref}]
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div key={msg.id} className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-stone-50 px-4 py-3">
                      <p className="text-sm leading-relaxed text-stone-700">
                        {msg.text}
                      </p>
                    </div>
                  </div>
                )
              )}
            </div>

            {/* Input area */}
            <div className="border-t border-stone-100 p-4">
              <div className="flex items-end gap-3">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Mesajini yaz..."
                  rows={2}
                  className="flex-1 resize-none rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-700 placeholder:text-stone-400 focus:border-[#C9A961] focus:outline-none focus:ring-1 focus:ring-[#C9A961]/30"
                />
                <button className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-[#C9A961] to-amber-500 text-white shadow-sm transition-all hover:shadow">
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Context panel */}
        <div className="hidden w-[200px] flex-shrink-0 lg:block">
          <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
            <h4 className="font-display mb-3 text-xs font-semibold uppercase tracking-wide text-stone-400">
              Baglam
            </h4>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-xs text-stone-400">Aktif proje</dt>
                <dd className="font-medium text-stone-700">MCDM Tezi</dd>
              </div>
              <div>
                <dt className="text-xs text-stone-400">Son ziyaret</dt>
                <dd className="font-medium text-stone-700">Bosluk Haritasi</dd>
              </div>
              <div>
                <dt className="text-xs text-stone-400">Defterde</dt>
                <dd className="font-medium text-stone-700">12 not</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
