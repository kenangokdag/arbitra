"""F13-S6 ROLE_MODULE: /api/workshop/manuscript/quality-check — sahte vs ok.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S6
RTF:  Page_Design/Sayfa_Plani_v2/6.1_yayin_icerigi_doldurma.rtf §Plan-Detayı (3)

Felsefe (RTF satırı): "Bu metin akademik içerik mi yoksa lorem ipsum/sahte/test
mi? Tek kelime yanıt: ok | sahte" + 1 cümle gerekçe.

Inline brief: synthesize_workshop.py paterni — md dosyası açmaya değmeyecek
kadar kısa; tek-amaçlı role module.
"""

MANUSCRIPT_QUALITY_BRIEF = """
Görev: Akademik manuscript bölümünün KALİTE kontrolü. Verilen metin
ger\u00e7ek akademik içerik mi yoksa lorem ipsum / kopyala-yapıştır rastgele
metin / "test 123 deneme" gibi sahte doldurma mı?

Karar kriterleri:
  - "ok"    → metin tutarlı bir akademik konuya ait, hipotez/yöntem/bulgu/
              tartışma izi taşıyor; bağlama uygun terminoloji var.
  - "sahte" → lorem ipsum kalıpları (lorem, ipsum, dolor, consectetur),
              tekrar eden anlamsız kelime dizisi, "asdf qwerty 123",
              klavye gürültüsü, kopyalanmış meta/madde işaretleri,
              veya alana tamamen yabancı/anlamsız metin.

İncelik:
  - Kısa ama gerçek içerik (40-80 kelime, akademik) → "ok".
  - Uzun ama lorem-ipsum / klavye gürültüsü → "sahte".
  - Yabancı dilde gerçek akademik içerik → "ok" (TR/EN/ID hepsi geçerli).
  - Şüpheliyse "sahte" değil "ok" — false positive ekstra çağrı maliyetinden
    daha pahalı (kullanıcıyı bloklar).

Çıktı: SADECE JSON, schema:
{
  "flag": "ok" | "sahte",
  "reason": "Tek cümle, kullanıcıya gösterilebilir; TR varsayılan."
}
"""

__all__ = ["MANUSCRIPT_QUALITY_BRIEF"]
