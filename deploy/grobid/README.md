# GROBID servisi — Railway (F14 hakemlik PDF kaynakça çıkarımı)

GROBID, PDF'ten yapılandırılmış kaynakça (TEI-XML) çıkaran bir servistir. F14
hakemlik ingestion'ı (`engine/ingestion/grobid_client.py`) `GROBID_URL` env'i
tanımlıysa kaynakçayı GROBID'ten (yüksek kalite) çeker; yoksa PyMuPDF
heuristic'ine düşer (fallback — GROBID ZORUNLU DEĞİL).

## Railway'de ayrı servis olarak deploy

GROBID papermind API'sinden **ayrı** bir Railway servisidir (kendi container'ı).

1. Railway → New Service → **Deploy from Docker image** (veya bu `deploy/grobid/Dockerfile`).
2. Image: **`grobid/grobid:0.8.1`** — ⚠️ DOĞRULA: deploy anında DockerHub'dan
   güncel stable tag'i teyit et (`grobid/grobid` resmi imaj). CRF-tabanlı imaj
   ~1GB RAM yeter; tam derin-öğrenme imajı (`grobid/grobid:...-full`) ~4GB+ ister
   ve kaynakça için gerekmez.
3. Port: GROBID **8070** dinler. Railway PORT'u otomatik proxy'ler; container
   8070'i expose eder.
4. Sağlık: `GET /api/isalive` → `true`.
5. Kaynak: en az 1GB RAM (CRF). Düşük trafikte küçük instance yeter.

## papermind tarafına bağlama

Deploy sonrası papermind API env'ine ekle (Railway/Render env veya `.env`):

```
GROBID_URL=https://<grobid-servis-adi>.up.railway.app
```

Bu kadar — `grobid_client.is_enabled()` GROBID_URL'i görünce devreye girer.
Güvenlik: `base_url()` yalnız http/https şemasına izin verir (S310 hardened).

## Doğrulama (deploy sonrası)

```bash
curl https://<grobid>.up.railway.app/api/isalive          # → true
# Bir PDF ile kaynakça çıkarımı:
curl -F input=@makale.pdf https://<grobid>.up.railway.app/api/processReferences | head
```

## CANLI (2026-06-22)
- **Railway proje:** Arbitra (id 6ea1c04b-0101-459d-bfb8-b8f88d7fa00a, gmail hesabı)
- **Servis:** grobid (image grobid/grobid:0.8.1) — deploy SUCCESS
- **URL:** https://grobid-production-a2c9.up.railway.app — `GET /api/isalive` → `true` (HTTP 200 doğrulandı)
- papermind/ARBITRA app deploy olunca: `GROBID_URL=https://grobid-production-a2c9.up.railway.app`
  (daha iyisi: app aynı Railway projesine gelince **private networking** ile public domain'siz bağla — OPEN_WORK)

## Not — OPEN_WORK
- GROBID kapalıyken (GROBID_URL unset) ingestion PyMuPDF heuristic'iyle çalışır;
  GROBID kaynakça doğruluğunu (özellikle düzensiz formatlarda) artırır.
- XML parse `defusedxml` ile sertleştirilmeli (şu an stdlib ET + try/except,
  S314 noqa'lı — GROBID admin-servisi olduğundan düşük risk).
