"use client";

// Ayarlar — KVKK hesap silme (tehlikeli bölge).
// Tek iş: hesap yönetimi; yıkıcı eylem (kalıcı silme) net AYRILMIŞ bir bölümde,
// var(--color-warn) ile işaretli. Silme → typed-confirmation diyalog (ConfirmDialog).
// Başarıda: clearToken() → / (pazarlama kökü, 2026-08-28: eski /landing). Dead-end yok: idle /
// yazım-geçersiz / gönderim / hata / başarı durumlarının hepsi ele alınır.

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, ShieldX, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { clearToken } from "@/lib/auth";
import {
  ACCOUNT_DELETE_PHRASE,
  deleteAccount,
} from "@/lib/account-api";

const DELETED_DATA = [
  "Makaleler ve projeler",
  "Notlar ve okuma listesi",
  "Hakem değerlendirmeleri ve raporlar",
  "Hesap ve profil bilgilerin",
];

export default function SettingsPage() {
  const router = useRouter();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="mx-auto w-full max-w-2xl">
      <PageHeader
        title="Ayarlar"
        lede="Hesabınla ilgili tercihleri buradan yönetebilirsin."
      />

      {/* Tehlikeli bölge — yıkıcı eylem, görsel olarak net ayrılmış */}
      <section
        aria-labelledby="danger-zone-title"
        className="overflow-hidden rounded-xl border"
        style={{
          borderColor: "color-mix(in oklab, var(--color-warn) 35%, var(--color-rule))",
          background: "var(--color-bg-card)",
        }}
      >
        <div
          className="flex items-center gap-2.5 border-b px-5 py-3.5"
          style={{
            background: "var(--color-warn-pale)",
            borderColor: "color-mix(in oklab, var(--color-warn) 25%, transparent)",
          }}
        >
          <ShieldX
            className="h-4 w-4 flex-shrink-0"
            style={{ color: "var(--color-warn)" }}
            strokeWidth={2}
            aria-hidden
          />
          <h2
            id="danger-zone-title"
            className="text-sm font-semibold"
            style={{ color: "var(--color-warn)" }}
          >
            Tehlikeli bölge — Hesabı sil (KVKK)
          </h2>
        </div>

        <div className="px-5 py-5">
          <p className="text-[14px] leading-relaxed text-ink-soft">
            Hesabını sildiğinde <strong className="font-semibold text-ink">tüm verin
            anında ve kalıcı olarak</strong> silinir. Bu işlem{" "}
            <strong className="font-semibold text-ink">geri alınamaz</strong> —
            yedek alınmaz, kurtarma yoktur. KVKK kapsamındaki{" "}
            <em>silme (unutulma) hakkın</em> uyarınca verin sunucularımızdan
            tamamen kaldırılır.
          </p>

          <div
            className="mt-4 rounded-lg border px-4 py-3"
            style={{
              borderColor: "var(--color-rule-soft)",
              background: "var(--color-bg-soft)",
            }}
          >
            <p className="mb-2 text-[12px] font-medium uppercase tracking-wide text-ink-faint">
              Silinecek veriler
            </p>
            <ul className="space-y-1.5">
              {DELETED_DATA.map((item) => (
                <li
                  key={item}
                  className="flex items-center gap-2 text-[13px] text-ink-mute"
                >
                  <Trash2
                    className="h-3.5 w-3.5 flex-shrink-0"
                    style={{ color: "var(--color-warn)" }}
                    aria-hidden
                  />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            className="mt-5 inline-flex items-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold transition-opacity hover:opacity-90"
            style={{ background: "var(--color-warn)", color: "var(--color-accent-fg)" }}
          >
            <Trash2 className="h-4 w-4" aria-hidden />
            Hesabımı kalıcı olarak sil
          </button>
        </div>
      </section>

      <ConfirmDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onConfirm={async () => {
          await deleteAccount(ACCOUNT_DELETE_PHRASE);
        }}
        onSuccess={() => {
          // Sunucu silmeyi onayladı → token'ı temizle, pazarlama köküne dön.
          clearToken();
          router.push("/");
        }}
        title="Hesabını kalıcı olarak sil"
        icon={AlertTriangle}
        confirmPhrase={ACCOUNT_DELETE_PHRASE}
        confirmLabel="Hesabımı sil"
        cancelLabel="Vazgeç"
        description={
          <>
            Bu işlem <strong className="font-semibold text-ink">geri alınamaz</strong>.
            Hesabın ve tüm verin (makaleler, projeler, notlar, değerlendirmeler)
            anında ve kalıcı olarak silinecek.
          </>
        }
        success={{
          title: "Hesabın silindi",
          description: "Verin kaldırıldı. Çıkış yapılıyor…",
        }}
      />
    </div>
  );
}
