"""
Zdroj: nehnutelnosti.sk - pozemky a domy na predaj v zvolených obciach (config.OBCE).

Overené 26.9.2026 v prehliadači:
  - URL: /vysledky/pozemky/<obec>/predaj a /vysledky/domy/<obec>/predaj (slug obce napr. liptovska-luzna).
    Kategórie 'chaty-chalupy' a 'stavebne-pozemky' s obcou v URL NEfungujú (presmerujú na zoznam za celé
    Slovensko) - preto len 'pozemky' (obsahujú všetky druhy pozemkov) a 'domy' (obsahujú aj chaty).
  - Stránka je server-side renderovaná; inzeráty sú v surovom HTML (odkazy `a[href*="/detail/<ID>/"]`, 5 na kartu,
    "karta" = najmenší spoločný predok). Hashované MUI triedy nepoužívame.
  - Poradie <p data-test-id="text"> v karte: lokalita ("..., okres X"), druh ("Lesy", "Rekreačný pozemok",
    "Rodinný dom"), plocha (nie vždy), cena ("28 100 €" alebo "Cena dohodou"), cena/m² (nie vždy), popis, realitka.
  - Obec bez inzerátov (napr. pozemky Liptovská Osada) vráti platnú stránku s nulou kariet - to NIE JE chyba.
    Platnosť stránky overujeme cez <h1> alebo <title> (prázdna stránka <h1> nemá - overené 26.9.2026 v prvom nasadení).
  - Detail: dvojice `<p>Plocha pozemku:</p><p>726 m²</p>` (aj Plocha domu, Územie, Voda, Elektrina...), celý popis
    v `<p id="detail-description">`, stav domu v meta description ("Dom, Predaj, Obec, Pôvodný stav, 150 m², ...").
"""

import re

from bs4 import BeautifulSoup

import config
import textutils
from http_util import SourceError, fetch

SOURCE_NAME = "nehnutelnosti_sk"
LABEL = "nehnutelnosti.sk"
REQUIRED = True

_ID_RE = re.compile(r"/detail/([^/]+)/")
_AREA_P = re.compile(r"^[\d\s .,]+m\s*[²2]$")
_PRICE_P = re.compile(r"^\d[\d\s .,]*€$")
_PPM2_P = re.compile(r"€\s*/\s*m\s*[²2]")
KNOWN_HOUSE_CONDITIONS = {"novostavba", "kompletna rekonstrukcia", "ciastocna rekonstrukcia", "povodny stav",
                          "vo vystavbe", "developersky projekt"}


def _card_for(anchors):
    first = anchors[0]
    ancestor_ids = [{id(p) for p in a.parents} for a in anchors[1:]]
    for parent in first.parents:
        if all(id(parent) in s for s in ancestor_ids):
            return parent
    return first.parent


def page_is_for(html: str, obec_label: str) -> bool:
    """
    True, ak je to skutočne výpis pre danú obec (a nie presmerovanie na zoznam za celé Slovensko).
    Kontroluje sa <h1> ("Pozemky na predaj, Liptovská Lúžna") ALEBO <title> ("Pozemky Liptovská Osada - ponuka ...").
    Titulok je nutný, lebo stránka bez inzerátov (napr. pozemky Liptovská Osada) <h1> nemá.
    """
    soup = BeautifulSoup(html, "html.parser")
    needle = textutils.fold(obec_label)
    h1 = soup.find("h1")
    if h1 and needle in textutils.fold(h1.get_text(" ", strip=True)):
        return True
    return bool(soup.title and needle in textutils.fold(soup.title.get_text(" ", strip=True)))


def parse_page(html: str, prop_type: str, obec_label: str) -> list[dict]:
    """Kandidáti z jednej stránky výpisu (bez filtrovania kritérií)."""
    soup = BeautifulSoup(html, "html.parser")
    by_id: dict[str, list] = {}
    order: list[str] = []
    for a in soup.select('a[href*="/detail/"]'):
        m = _ID_RE.search(a["href"])
        if not m:
            continue
        pid = m.group(1)
        if pid not in by_id:
            by_id[pid] = []
            order.append(pid)
        by_id[pid].append(a)

    candidates = []
    for pid in order:
        anchors = by_id[pid]
        card = _card_for(anchors)
        h2 = card.find("h2")
        title = h2.get_text(" ", strip=True) if h2 else ""
        paragraphs = []
        for p in card.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text and text not in paragraphs:
                paragraphs.append(text)

        location = next((t for t in paragraphs if "okres" in t), None)
        loc_idx = paragraphs.index(location) if location else -1
        area_text = next((t for t in paragraphs if _AREA_P.match(t)), None)
        price_text = next((t for t in paragraphs if _PRICE_P.match(t)), None)
        negotiable = next((t for t in paragraphs if textutils.is_negotiable_price(t)), None)
        ppm2_text = next((t for t in paragraphs if _PPM2_P.search(t)), None)
        subtype = None
        if loc_idx >= 0 and loc_idx + 1 < len(paragraphs):
            cand = paragraphs[loc_idx + 1]
            if not (_AREA_P.match(cand) or _PRICE_P.match(cand) or textutils.is_negotiable_price(cand)
                    or _PPM2_P.search(cand)) and len(cand) < 40:
                subtype = cand
        used = {title, location, area_text, price_text, negotiable, ppm2_text, subtype}
        description = max((t for t in paragraphs if t not in used and len(t) >= 40 and not _PPM2_P.search(t)),
                          key=len, default="")

        img = card.find("img", src=re.compile(r"^https?://"))
        href = anchors[0]["href"]
        candidates.append({
            "portal_id": pid,
            "source": SOURCE_NAME,
            "url": href if href.startswith("http") else config.BASE_NEHNUTELNOSTI + href,
            "title": title,
            "description_raw": description,
            "prop_type": prop_type,
            "subtype": subtype,
            "obec": obec_label,
            "location": location,
            "area_m2": textutils.parse_area(area_text),
            "price": textutils.parse_price(price_text),
            "price_note": None if price_text else negotiable,
            "price_per_m2": textutils.parse_price_per_m2(ppm2_text),
            "main_photo_url": img["src"] if img else None,
        })
    return candidates


def parse_detail(html: str) -> dict:
    """
    Údaje z detailu: plocha pozemku / domu, územie, vlastníctvo, siete, stav domu, celý popis.
    Dvojice label/hodnota sú za sebou idúce `<p data-test-id="text">`: label končí ':'; ak za labelom hneď
    nasleduje ďalší label, hodnota chýba (None).
    """
    soup = BeautifulSoup(html, "html.parser")
    texts = [p.get_text(" ", strip=True) for p in soup.find_all("p", attrs={"data-test-id": "text"})]
    pairs: dict[str, str | None] = {}
    for i, t in enumerate(texts):
        if t.endswith(":") and len(t) < 40:
            nxt = texts[i + 1] if i + 1 < len(texts) else None
            pairs[t[:-1].strip()] = None if (nxt is None or nxt.endswith(":")) else nxt

    util = []
    for label, key in (("Voda", "voda"), ("Elektrina", "elektrina"), ("Plyn", "plyn"), ("Kanalizácia", "kanalizacia")):
        if pairs.get(label):
            util.append(f"{key}={pairs[label]}")

    meta = soup.find("meta", attrs={"name": "description"})
    parts = [p.strip() for p in ((meta.get("content") or "") if meta else "").split(",")]
    condition = None
    if len(parts) > 3 and textutils.fold(parts[3]) in KNOWN_HOUSE_CONDITIONS:
        condition = parts[3]

    desc_el = soup.find(id="detail-description")
    return {
        "plot_area_m2": textutils.parse_area(pairs.get("Plocha pozemku")),
        "house_area_m2": textutils.parse_area(pairs.get("Plocha domu") or pairs.get("Úžitková plocha")),
        "built_area_m2": textutils.parse_area(pairs.get("Zastavaná plocha")),
        "territory": pairs.get("Územie"),
        "ownership": pairs.get("Vlastníctvo"),
        "condition_label": condition,
        "utilities": ";".join(util) or None,
        "description": desc_el.get_text("\n", strip=True) if desc_el else "",
    }


def fetch_detail(url: str) -> dict:
    page = fetch(url, f"[{SOURCE_NAME}] detail")
    return parse_detail(page.text)


def fetch_all() -> list[dict]:
    """Stiahne všetky kombinácie kategória x obec. Vyhodí SourceError pri blokovaní / zmenenej štruktúre."""
    prefix = f"[{SOURCE_NAME}]"
    results: dict[str, dict] = {}
    for cat, prop_type in config.KATEGORIE:
        for slug, obec_label in config.OBCE:
            base = config.NEHNUTELNOSTI_URL.format(cat=cat, obec=slug)
            for page_no in range(1, config.MAX_PAGES_PER_QUERY + 1):
                url = base if page_no == 1 else f"{base}?page={page_no}"
                page = fetch(url, prefix)
                if not page_is_for(page.text, obec_label):
                    raise SourceError("structure", f"stránka {url} nie je výpisom pre '{obec_label}' "
                                                   f"(presmerovanie alebo zmena štruktúry)")
                candidates = parse_page(page.text, prop_type, obec_label)
                print(f"{prefix} {cat} / {obec_label}: strana {page_no}, {len(candidates)} inzerátov")
                for c in candidates:
                    results.setdefault(c["portal_id"], c)
                if len(candidates) < config.PAGE_SIZE:
                    break
            else:
                raise SourceError("structure", f"viac než {config.MAX_PAGES_PER_QUERY} strán pre {base}")
    return list(results.values())
