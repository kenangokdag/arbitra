"""F13-S4 5.4 — citation formatter yardımcıları."""

from __future__ import annotations


def split_name(full: str) -> tuple[str, str]:
    """'Surname, First Middle' veya 'First Middle Surname' → (surname, given).

    Heuristik: virgül varsa öncesi soyad; yoksa son kelime soyad.
    """
    if "," in full:
        surname, given = full.split(",", 1)
        return surname.strip(), given.strip()
    parts = full.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def initials(given: str) -> str:
    """'First Middle' → 'F. M.'."""
    if not given:
        return ""
    return ". ".join(p[0].upper() for p in given.split() if p) + "."


def joined_apa_authors(authors: list[str]) -> str:
    """APA: 'Surname, F. M., & Surname2, F.'"""
    pieces: list[str] = []
    for a in authors:
        s, g = split_name(a)
        if not s:
            continue
        if g:
            pieces.append(f"{s}, {initials(g)}")
        else:
            pieces.append(s)
    if not pieces:
        return ""
    if len(pieces) == 1:
        return pieces[0]
    return ", ".join(pieces[:-1]) + ", & " + pieces[-1]


def joined_vancouver_authors(authors: list[str]) -> str:
    """Vancouver: 'Surname FM, Surname2 F.' (initials without dots, max 6 + et al.)."""
    pieces: list[str] = []
    for a in authors:
        s, g = split_name(a)
        if not s:
            continue
        ini = "".join(p[0].upper() for p in g.split() if p)
        pieces.append(f"{s} {ini}".strip())
    if len(pieces) > 6:
        return ", ".join(pieces[:6]) + ", et al"
    return ", ".join(pieces)


def joined_ieee_authors(authors: list[str]) -> str:
    """IEEE: 'F. M. Surname and F. Surname2'."""
    pieces: list[str] = []
    for a in authors:
        s, g = split_name(a)
        if not s:
            continue
        pieces.append(f"{initials(g)} {s}".strip() if g else s)
    if not pieces:
        return ""
    if len(pieces) == 1:
        return pieces[0]
    return ", ".join(pieces[:-1]) + " and " + pieces[-1]


def joined_chicago_authors(authors: list[str]) -> str:
    """Chicago: 'Surname, First, and First Surname2.'"""
    pieces: list[str] = []
    for i, a in enumerate(authors):
        s, g = split_name(a)
        if not s:
            continue
        if i == 0:
            pieces.append(f"{s}, {g}" if g else s)
        else:
            pieces.append(f"{g} {s}".strip() if g else s)
    if not pieces:
        return ""
    if len(pieces) == 1:
        return pieces[0]
    return ", and ".join([", ".join(pieces[:-1]), pieces[-1]])


def joined_mla_authors(authors: list[str]) -> str:
    """MLA: 'Surname, First, and First Surname2.' veya 'Surname, First, et al.'"""
    if len(authors) > 3:
        s, g = split_name(authors[0])
        return f"{s}, {g}, et al."
    return joined_chicago_authors(authors)


__all__ = [
    "initials",
    "joined_apa_authors",
    "joined_chicago_authors",
    "joined_ieee_authors",
    "joined_mla_authors",
    "joined_vancouver_authors",
    "split_name",
]
