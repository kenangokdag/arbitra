# F14 hakemlik — GROBID servisi (Railway, ayrı container)
# Çalışma ortamı Dockerfile ile deklare (CANON/cloud-compute). Secret yok —
# GROBID stateless; papermind tarafı GROBID_URL env'i ile bağlanır.
#
# ⚠️ DOĞRULA (deploy anında): grobid/grobid resmi imajının güncel stable tag'i.
# CRF imajı (~1GB RAM) kaynakça için yeter; *-full (deep-learning, ~4GB+) gereksiz.
FROM grobid/grobid:0.8.1

# GROBID 8070 dinler; Railway PORT'u proxy'ler.
EXPOSE 8070

# Sağlık ucu: GET /api/isalive → true
# Kaynakça ucu (grobid_client kullanır): POST /api/processReferences
