# F14-S3 — ARBITRA api (FastAPI) container imajı.
#
# KULLANILMIYOR — aktif deploy Render (deploy/render.yaml, env: python native
# buildpack; bu Dockerfile'ı HİÇ görmez/çalıştırmaz). 2026-08-17'de Railway
# vs Render tutarsızlığı netleştirildi (Kenan kararı: Render) — railway.json
# kaldırıldı, bu dosya yerel `docker build` / olası ileride containerize
# deploy ihtiyacı için TUTULDU, "Railway" markası temizlendi.
#
# uv ile deterministik kurulum. Çalışma dizini /app; engine/ config/ scripts/
# cwd üzerinden import edilir (pyproject packages=["api"]; diğer paketler
# kaynak ağacından gelir).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv

# 1) Bağımlılık katmanı (kod değişince yeniden çözülmesin — torch ağır)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

# 2) Kaynak + projeyi kur
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
# $PORT container platformu tarafından enjekte edilirse kullanılır; yoksa 8000.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
