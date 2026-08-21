#!/usr/bin/env bash
# N-6 (2026-05-27): Idempotent migration applier.
# Audit ref: AUDIT_REPORT.md §11 N-6.
#
# Çalışma:
#   1) db/migrations/*.sql dosyalarını lexicographic sırayla tarar.
#   2) Her dosya için version = basename .sql olarak hesaplanır.
#   3) public.schema_migrations tablosuna BAKILIR; satır varsa SKIP.
#   4) Yoksa psql ile dosya çalıştırılır. Migration kendi içinde BEGIN/COMMIT
#      ve INSERT INTO schema_migrations satırını içermeli (0001..0040 hepsi
#      bu pattern'i kullanır).
#
# Kullanım:
#   DATABASE_URL=postgresql://... bash scripts/apply_migrations.sh
#   bash scripts/apply_migrations.sh --dry-run   # sadece sıradakileri listele
#
# Çıkış:
#   0 → her şey başarılı veya yoktur
#   1 → DATABASE_URL eksik / psql yok / migration başarısız

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL ortam değişkeni gerekli." >&2
  echo "Örnek: export DATABASE_URL=postgresql://user:pass@host:5432/db" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql bulunamadı (PATH'e ekleyin: brew install libpq && brew link --force libpq)." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIG_DIR="$(cd "${SCRIPT_DIR}/../db/migrations" && pwd)"

echo "🔍 Migration dizini: ${MIG_DIR}"
echo "🔍 DB: ${DATABASE_URL%@*}@***"

# schema_migrations tablosu yoksa (ilk çalıştırma) 0001 onu yaratır.
applied_versions=""
if psql "${DATABASE_URL}" -At -c "SELECT to_regclass('public.schema_migrations')" 2>/dev/null | grep -q schema_migrations; then
  applied_versions="$(psql "${DATABASE_URL}" -At -c "SELECT version FROM public.schema_migrations ORDER BY version")"
fi

applied=0
skipped=0

for f in "${MIG_DIR}"/*.sql; do
  version="$(basename "${f}" .sql)"
  if echo "${applied_versions}" | grep -qx "${version}"; then
    skipped=$((skipped + 1))
    continue
  fi

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  DRY-RUN apply: ${version}"
    applied=$((applied + 1))
    continue
  fi

  echo "  ▶ apply: ${version}"
  if ! psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${f}"; then
    echo "ERROR: ${version} migration başarısız — durdu." >&2
    exit 1
  fi
  applied=$((applied + 1))
done

echo "✅ Tamamlandı. Uygulandı: ${applied}, atlandı: ${skipped}"
