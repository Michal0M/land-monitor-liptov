"""HTML vzorky zostavené podľa REÁLNEJ štruktúry nehnutelnosti.sk overenej 26.9.2026 (texty z reálnych inzerátov)."""


def card(pid, title, ps, img="https://img.unitedclassifieds.sk/foto/x_fss?st=1"):
    anchors = "".join(f'<a href="https://www.nehnutelnosti.sk/detail/{pid}/slug">odkaz</a>' for _ in range(3))
    paras = "".join(f'<p data-test-id="text">{p}</p>' for p in ps)
    return (f'<div class="outer"><div class="card">{anchors}<img src="{img}"><h2>{title}</h2>{paras}'
            f'<a href="https://www.nehnutelnosti.sk/detail/{pid}/slug">viac</a><a href="https://www.nehnutelnosti.sk/detail/{pid}/slug">x</a>'
            f'</div></div>')


def page(h1, cards):
    return f'<html><head><title>{h1}</title></head><body><h1>{h1}</h1><main>{"".join(cards)}</main></body></html>'


LAND_LL = card("Ju9GhH98kPx", "Pozemky v čarokrásnych Nízkych Tatrách - Liptovská Lúžna",
               ["Liptovská Lúžna, okres Ružomberok", "Lesy", "56227 m²", "28 100 €", "0,5 €/m²",
                "Ponúkame na predaj podiel v urbárskom spoločenstve - Urbariát - Pozemkové spoločenstvo Liptovská Lúžna.",
                "Broker Consulting, a.s.", "Poľnohospodárske a lesné pozemky Liptovská Lúžna Predaj"])
LAND_REV = card("JuBljyO8hbi", "Rekreačný pozemok v obci Liptovské Revúce ID: N041-14-STKa",
                ["Hlavná, Liptovské Revúce, okres Ružomberok", "Rekreačný pozemok", "726 m²", "73 300 €", "100,96 €/m²",
                 "ID: N041-14-STKa  Ponúkam na predaj pozemok situovaný v krásnom horskom prostredí Liptovské Revúce.",
                 "Nové bývanie", "Rekreačný pozemok Slovensko Predaj"])
HOUSE_NEGOTIABLE = card("Ju5WlUoNnF_", "Na predaj útulný rodinný dom v krásnej prírode- Liptovská Lúžna ",
                        ["Liptovská Lúžna, okres Ružomberok", "Rodinný dom", "150 m²", "Cena dohodou",
                         "Ak hľadáte pokojné bývanie alebo chalupu na víkendový relax uprostred liptovskej prírody, ...",
                         "OVERENÉ REALITY", "Domy Liptovská Lúžna Predaj"])
HOUSE_NOAREA = card("JuXWfmmUD8x", "HALO reality - Predaj, rodinný dom Liptovská Lúžna - ZNÍŽENÁ CENA",
                    ["Liptovská Lúžna, okres Ružomberok", "Rodinný dom", "69 900 €",
                     "Realitná kancelária HALO reality a Mgr. Marián Hlavna, kontakt: 0944 515 056, nehnuteľnosť",
                     "HALO reality, s.r.o.", "Domy Liptovská Lúžna Predaj"])
HOUSE_DUPLOC = card("Ju8WZpgHGL1", "Rodinný dom v centre obce /841 m2/ Liptovské Revúce",
                    ["Liptovské Revúce, Liptovské Revúce, okres Ružomberok", "Rodinný dom", "841 m²", "185 500 €",
                     "220,57 €/m²", "Reality Alpia Vám ponúkajú na predaj čiastočne zrekonštruovaný dom v obci Liptovské Revúce",
                     "Reality Alpia", "Domy Liptovské Revúce Predaj"])

PAGE_LAND_LL = page("Pozemky na predaj, Liptovská Lúžna", [LAND_LL])
PAGE_LAND_OSADA_EMPTY = page("Pozemky na predaj, Liptovská Osada", [])
PAGE_HOUSES_LL = page("Domy na predaj, Liptovská Lúžna", [HOUSE_NEGOTIABLE, HOUSE_NOAREA])
PAGE_GENERIC_REDIRECT = page("Stavebné pozemky na predaj, Slovensko", [LAND_LL])

DETAIL_LAND = """<html><head><meta name="description" content="Pozemok, Predaj, Liptovské Revúce, undefined, 726 m², 73 300 €, ID: N041..."></head>
<body><main>
<p data-test-id="text">Plocha pozemku:</p><p data-test-id="text">726 m²</p>
<p data-test-id="text">Vlastnosti nehnuteľnosti</p>
<p data-test-id="text">Vlastníctvo:</p><p data-test-id="text">Osobné</p>
<p data-test-id="text">Územie:</p><p data-test-id="text">Intravilán</p>
<p data-test-id="text">Voda:</p><p data-test-id="text">Verejný vodovod</p>
<p data-test-id="text">Elektrina:</p>
<p data-test-id="text">Plyn:</p><p data-test-id="text">Nedostupné</p>
<p id="detail-description" data-test-id="text">Ponúkam na predaj pozemok.
Pozemok je možné rozdeliť podľa geometrického plánu.
Dostupnosť inžinierskych sietí: elektrika, voda v dostupnosti do 50m.</p>
</main></body></html>"""

DETAIL_HOUSE = """<html><head><meta name="description" content="Dom, Predaj, Liptovské Revúce, Pôvodný stav, 150 m², 166 000 €, Hľadáte bývanie..."></head>
<body><main>
<p data-test-id="text">Plocha domu:</p><p data-test-id="text">150 m²</p><p data-test-id="text">Pôvodný stav</p>
<p data-test-id="text">Rok výstavby:</p><p data-test-id="text">1973</p>
<p data-test-id="text">Plocha pozemku:</p><p data-test-id="text">1 060 m²</p>
<p data-test-id="text">Zastavaná plocha:</p>
<p data-test-id="text">Vlastníctvo:</p><p data-test-id="text">Osobné</p>
<p data-test-id="text">Územie:</p><p data-test-id="text">Intravilán</p>
<p id="detail-description" data-test-id="text">Dom stojí na pozemku 1060 m2.</p>
</main></body></html>"""
