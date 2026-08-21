"""Global app teması — admin düzenler (FAZ 4A).

Tek doğruluk SÖZLEŞMESİ: GET/PATCH /api/app/theme + theme_service + DB
(app_theme_settings, migration 0043) hepsi bu modeli kullanır.

Yasa:
  - extra="forbid": bilinmeyen alan reddedilir.
  - Renkler hex (#RRGGBB) regex doğrulanır → geçersiz girdi ValidationError (422).
  - Fontlar named-constant allowlist'ten: sans ⟂ serif ayrı set; off-list reject.
  - updated_by/updated_at opsiyonel: response'ta döner, body'de göz ardı edilir
    (set_theme server-side yazar).
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Font allowlist'leri (named-constant — off-list reddi tek kaynaktan). globals.css
# var(--font-inter)/var(--font-lora) ile hizalı; sans ve serif AYRI set (bir serif
# fontu sans alanına yazılamaz, tersi de).
FONT_SANS_ALLOWLIST: Final[frozenset[str]] = frozenset({"inter", "source-sans"})
FONT_SERIF_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {"lora", "newsreader", "source-serif"}
)

# #RRGGBB — 6 haneli hex (kısa #RGB veya rgba() KABUL EDİLMEZ; FE token sözleşmesi
# 6-hane bekler). Büyük/küçük harf serbest.
_HEX_COLOR_PATTERN: Final[str] = r"^#[0-9a-fA-F]{6}$"


class ThemeSettings(BaseModel):
    """Global app teması — 5 düzenlenebilir alan + opsiyonel künye."""

    model_config = ConfigDict(extra="forbid")

    accent_color: str = Field(..., pattern=_HEX_COLOR_PATTERN)
    bg_color: str = Field(..., pattern=_HEX_COLOR_PATTERN)
    ink_color: str = Field(..., pattern=_HEX_COLOR_PATTERN)
    font_sans: str
    font_serif: str

    # response künyesi (body'de gönderilse de set_theme override eder).
    updated_by: str | None = None
    updated_at: datetime | None = None

    @field_validator("font_sans")
    @classmethod
    def _check_font_sans(cls, v: str) -> str:
        if v not in FONT_SANS_ALLOWLIST:
            raise ValueError(
                f"font_sans must be one of {sorted(FONT_SANS_ALLOWLIST)}; got {v!r}"
            )
        return v

    @field_validator("font_serif")
    @classmethod
    def _check_font_serif(cls, v: str) -> str:
        if v not in FONT_SERIF_ALLOWLIST:
            raise ValueError(
                f"font_serif must be one of {sorted(FONT_SERIF_ALLOWLIST)}; got {v!r}"
            )
        return v


# Kod-varsayılanı: globals.css değerleri (web/src/styles/globals.css:13/21/31/47/48).
# DB'de satır yoksa / Supabase yoksa get_theme bunu döndürür → görsel değişmez.
def default_theme() -> ThemeSettings:
    return ThemeSettings(
        accent_color="#4F46E5",
        bg_color="#f8fafc",
        ink_color="#0f172a",
        font_sans="inter",
        font_serif="lora",
    )


__all__ = [
    "FONT_SANS_ALLOWLIST",
    "FONT_SERIF_ALLOWLIST",
    "ThemeSettings",
    "default_theme",
]
