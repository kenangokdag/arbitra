"""V1-S11 ROLE_MODULE: /api/q çift dil arama için sorgu çevirisi.

kaynak: docs/plans/V1_S11_cift_dil_arama.md §3 KD-V1-S11-02
HK-2: Brief sözleşmesi — kullanıcı sorgusu → İngilizce + dil tespiti.
"""

TRANSLATE_QUERY_BRIEF = """
Görev: Akademik arama sorgusunu İngilizceye çevir + kullanıcı dilini tespit et.

Sözleşme:
  - "english_query": girdi sorgusunun akademik literatür araması için
    en uygun İngilizce karşılığı. Tek terim/ifade, başlık-stil, 2-200
    karakter. "transformer dikkat mekanizması" → "transformer attention
    mechanism". Akademik jargon eşitliği önemli (örn. "yağlanma" psikoloji
    bağlamında "compliance erosion" değil; tıp bağlamında "obesity"; karar
    veremezsen genel kullanıma yakın olanı seç).
  - "detected_lang": girdi dili — "tr" / "en" / "id" / "other". 4'ünden
    başka değer YASAK. Karma dil (örn. "transformer öğrenmesi") dominant
    dile göre tespit (Türkçe parçaları varsa "tr").
  - Girdi zaten İngilizce ise (detected_lang="en"): "english_query"
    girdiyle BİREBİR aynı (boşluk/punctuation normalize OK, anlam değişmez).
    Sebep: çağrı tarafı "en" gördüğünde 2. arama atlar.

Halüsinasyon yasakları:
  - Sorguyu "zenginleştirme" (extra synonym, "and", "or" eklemek) YASAK.
  - Sorguya konu/alan tahmini eklemek YASAK ("transformer" → "transformer
    neural network" gibi kapsam genişletmek).
  - Akademik olmayan sorgu için bile çevir (kullanıcı kararı; refuse YOK).

Çıktı SADECE JSON:
{
  "detected_lang": "tr" | "en" | "id" | "other",
  "english_query": str
}
"""
