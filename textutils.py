"""Pomocné funkcie na čísla a text z inzerátov (bez diakritiky/malými písmenami cez fold())."""

import re
import unicodedata

NBSP = " "


def fold(text: str | None) -> str:
    """Malé písmená, bez diakritiky, zjednotené medzery."""
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", text.replace(NBSP, " ")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", s)


def parse_price(text: str | None) -> float | None:
    """'28 100 €' -> 28100.0, '73 300 €' -> 73300.0. Cena za m² ('0,5 €/m²') a 'Cena dohodou' -> None."""
    if not text:
        return None
    t = text.replace(NBSP, " ").strip()
    if re.search(r"€\s*/\s*m\s*[²2]", t):
        return None
    m = re.search(r"(\d[\d ]*(?:[.,]\d{1,2})?)\s*€", t)
    if not m:
        return None
    try:
        return float(m.group(1).replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def parse_price_per_m2(text: str | None) -> float | None:
    """'100,96 €/m²' -> 100.96, '1 106,67 €/m²' -> 1106.67."""
    if not text:
        return None
    m = re.search(r"(\d[\d ]*(?:[.,]\d+)?)\s*€\s*/\s*m\s*[²2]", text.replace(NBSP, " "))
    if not m:
        return None
    return float(m.group(1).replace(" ", "").replace(",", "."))


def parse_area(text: str | None) -> float | None:
    """'56227 m²' -> 56227.0, '56 227 m²' -> 56227.0, '77,63 m2' -> 77.63."""
    if not text:
        return None
    m = re.search(r"(\d[\d ]*(?:[.,]\d+)?)\s*m\s*[²2]", text.replace(NBSP, " "))
    if not m:
        return None
    return float(m.group(1).replace(" ", "").replace(",", "."))


def is_negotiable_price(text: str | None) -> bool:
    """'Cena dohodou', 'Cena na vyžiadanie', 'Info u RK' - cena nie je číslo."""
    t = fold(text)
    return bool(re.match(r"^(cena (dohodou|na vyziadanie|v rk|nezname)|dohodou|info u rk)", t))


# ------------------------------------------------------------------ príznaky z popisu

# Podiel/urbár: len skutočný predaj podielu v spoločenstve, NIE bežná zmienka "1/2 podiel na prístupovej ceste".
_SHARE = re.compile(r"urbar|pozemkov\w* spolocenstv|spoluvlastnick\w* podiel|podiel (?:v|vo) |"
                    r"podiel na (?:lese|lesoch|pozemkoch|polnohospodarskych)")
_SPLIT = re.compile(r"\bdelen|\bdelit|rozdel(?:it|en\w*)|odclen|geometrick|parcelac|parceliz|"
                    r"po rozdeleni|cast(?:i)? pozemku")
_UTIL = {
    "voda": re.compile(r"vodovod|studn|voda\b"),
    "elektrina": re.compile(r"elektri"),
    "kanalizacia": re.compile(r"kanaliz|zumpa|septik|zumpy"),
    "plyn": re.compile(r"\bplyn"),
}


def detect_flags(title: str | None, description: str | None, prop_type: str) -> list[str]:
    """
    Príznaky, ktoré sa na karte ukážu ako badge:
      share      - predáva sa PODIEL / urbárske (spoluvlastnícke) pozemky, nie samostatná parcela
      split      - pozemok je delený / z väčšieho celku / dá sa rozdeliť (geometrický plán, odčlenenie)
      half_house - polovica domu / dvojdomu
    """
    text = fold(f"{title or ''}. {description or ''}")
    flags = []
    if _SHARE.search(text):
        flags.append("share")
    if prop_type == "pozemok" and _SPLIT.search(text):
        flags.append("split")
    if prop_type == "dom" and re.search(r"polovic\w* (rodinneho )?(domu|dvojdomu)|polovica dvojdomu", fold(title)):
        flags.append("half_house")
    return flags


def utilities_from_text(description: str | None) -> dict[str, bool]:
    """Ktoré siete popis zmieňuje (voda, elektrina, kanalizácia, plyn) - len hrubý odhad, ak detail nemá pole."""
    text = fold(description)
    return {name: bool(rx.search(text)) for name, rx in _UTIL.items() if rx.search(text)}
