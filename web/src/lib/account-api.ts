// KVKK hesap silme — FE API katmanı.
// Backend sözleşmesi: DELETE /api/account (auth zorunlu, Bearer).
//   body: { confirm_phrase: "HESABIMI SİL" }  (birebir string)
//   400 → onay metni eşleşmedi; 200 → silindi + makbuz özeti.
// apiFetch DELETE + JSON body destekler (lib/api.ts:18,35).

import { ApiError, apiFetch } from "./api";

/** Kullanıcının tam olarak yazması gereken onay metni (backend ile birebir). */
export const ACCOUNT_DELETE_PHRASE = "HESABIMI SİL";

/**
 * Backend silme makbuzu özeti. Backend alan adları kesinleşene kadar gevşek
 * tutulur (opsiyonel) — render eden taraf yokluğa dayanıklı davranır.
 * Bilinen olası alanlar; gelmezse UI yine de başarıyı gösterir.
 */
export type AccountDeletionReceipt = {
  deleted?: boolean;
  user_id?: string;
  deleted_at?: string;
  // Silinen kayıt sayıları (varsa) — "ALL data" şeffaflığı için.
  deleted_counts?: Record<string, number>;
  message?: string;
  [key: string]: unknown;
};

/**
 * Hesabı kalıcı, geri-dönüşsüz sil (KVKK silme hakkı).
 * @param confirmPhrase Kullanıcının yazdığı onay metni — backend birebir doğrular.
 * @throws ApiError 400 onay metni eşleşmezse; 401 oturum geçersizse; 5xx sunucu hatası.
 */
export async function deleteAccount(
  confirmPhrase: string,
): Promise<AccountDeletionReceipt> {
  return apiFetch<AccountDeletionReceipt>("/api/account", {
    method: "DELETE",
    body: { confirm_phrase: confirmPhrase },
  });
}

export { ApiError };
