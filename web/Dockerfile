# F14-S3 — ARBITRA web (Next.js 16) container imajı. Context = web/ (bu dizin).
#
# KULLANILMIYOR — backend Render'a deploy ediliyor (2026-08-17 kararı); frontend
# deploy platformu (Vercel / Render static) henüz netleşmedi, ayrı iş. Bu
# dosya yerel `docker build` / olası ileride containerize deploy ihtiyacı
# için TUTULDU, "Railway" markası temizlendi.
#
# NEXT_PUBLIC_API_URL build-time gömülür (R-2): api domain'i build'den ÖNCE bilinmeli.
FROM node:24-slim AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

EXPOSE 3000
# $PORT container platformu tarafından enjekte edilirse kullanılır; yoksa 3000.
CMD ["sh", "-c", "npm start -- -p ${PORT:-3000}"]
