import os
import tempfile
import unittest
from unittest import mock

import config
import db
import nehnutelnosti_scraper as ns
import notify
import render
import scraper
import textutils as tu
from tests import fixtures as fx


class TextutilsTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(tu.parse_price("28 100 €"), 28100.0)
        self.assertIsNone(tu.parse_price("0,5 €/m²"))
        self.assertIsNone(tu.parse_price("Cena dohodou"))
        self.assertEqual(tu.parse_area("56227 m²"), 56227.0)
        self.assertEqual(tu.parse_area("1 060 m²"), 1060.0)
        self.assertEqual(tu.parse_price_per_m2("1 106,67 €/m²"), 1106.67)
        self.assertTrue(tu.is_negotiable_price("Cena dohodou"))
        self.assertFalse(tu.is_negotiable_price("73 300 €"))

    def test_flags(self):
        f = tu.detect_flags("Pozemky", "Predávame podiel v urbárskom spoločenstve", "pozemok")
        self.assertIn("share", f)
        f = tu.detect_flags("Pozemok", "Možnosť rozdeliť pozemok podľa geometrického plánu", "pozemok")
        self.assertIn("split", f)
        self.assertNotIn("split", tu.detect_flags("Dom", "Dispozícia rozdelená na izby, geometrický plán", "dom"))
        self.assertIn("half_house", tu.detect_flags("Na predaj polovica rodinného domu", "", "dom"))
        # dom s "podielom" (spoluvlastníctvo polovice domu) NIE je urbár
        self.assertEqual(tu.detect_flags("Polovica rodinného domu", "predaj spoluvlastníckeho podielu 1/2", "dom"),
                         ["half_house"])
        self.assertEqual(tu.detect_flags("Pozemok", "Rovinatý slnečný pozemok", "pozemok"), [])
        # reálny text: 1/2 podiel na prístupovom pozemku NIE je predaj podielu
        real = "Kupujúci s predajom získava aj 1/2 podiel na prístupovom pozemku o rozlohe 207 m2."
        self.assertNotIn("share", tu.detect_flags("Rekreačný pozemok", real, "pozemok"))
        self.assertIn("split", tu.detect_flags("Pozemok", "Pozemok je rozdelený na dve parcely", "pozemok"))
        self.assertIn("split", tu.detect_flags("Pozemok", "Možnosť rozdelenia pozemku", "pozemok"))


class ParserTests(unittest.TestCase):
    def test_land_cards(self):
        c = ns.parse_page(fx.PAGE_LAND_LL, "pozemok", "Liptovská Lúžna")
        self.assertEqual(len(c), 1)
        c = c[0]
        self.assertEqual(c["portal_id"], "Ju9GhH98kPx")
        self.assertEqual(c["subtype"], "Lesy")
        self.assertEqual(c["area_m2"], 56227.0)
        self.assertEqual(c["price"], 28100.0)
        self.assertEqual(c["price_per_m2"], 0.5)
        self.assertTrue(c["description_raw"].startswith("Ponúkame na predaj podiel"))
        self.assertTrue(c["main_photo_url"].startswith("https://"))

    def test_house_cards(self):
        c = {x["portal_id"]: x for x in ns.parse_page(fx.PAGE_HOUSES_LL, "dom", "Liptovská Lúžna")}
        self.assertEqual(len(c), 2)
        neg = c["Ju5WlUoNnF_"]                       # ID s podčiarkovníkom
        self.assertIsNone(neg["price"])
        self.assertEqual(neg["price_note"], "Cena dohodou")
        self.assertEqual(neg["area_m2"], 150.0)
        noarea = c["JuXWfmmUD8x"]
        self.assertIsNone(noarea["area_m2"])
        self.assertEqual(noarea["price"], 69900.0)
        self.assertEqual(noarea["subtype"], "Rodinný dom")

    def test_page_validity(self):
        self.assertTrue(ns.page_is_for(fx.PAGE_LAND_LL, "Liptovská Lúžna"))
        self.assertTrue(ns.page_is_for(fx.PAGE_LAND_OSADA_EMPTY, "Liptovská Osada"))
        self.assertFalse(ns.page_is_for(fx.PAGE_GENERIC_REDIRECT, "Liptovská Lúžna"))
        self.assertEqual(ns.parse_page(fx.PAGE_LAND_OSADA_EMPTY, "pozemok", "Liptovská Osada"), [])

    def test_detail_land(self):
        d = ns.parse_detail(fx.DETAIL_LAND)
        self.assertEqual(d["plot_area_m2"], 726.0)
        self.assertEqual(d["territory"], "Intravilán")
        self.assertEqual(d["ownership"], "Osobné")
        self.assertEqual(d["utilities"], "voda=Verejný vodovod;plyn=Nedostupné")   # Elektrina bez hodnoty
        self.assertIsNone(d["condition_label"])                                    # 'undefined' v meta
        self.assertIn("\n", d["description"])

    def test_detail_house(self):
        d = ns.parse_detail(fx.DETAIL_HOUSE)
        self.assertEqual(d["house_area_m2"], 150.0)
        self.assertEqual(d["plot_area_m2"], 1060.0)
        self.assertEqual(d["condition_label"], "Pôvodný stav")
        self.assertIsNone(d["built_area_m2"])          # 'Zastavaná plocha:' bez hodnoty
        # reálny dom HALO reality (26.9.2026): bez plochy domu, len pozemok 164 m² a zastavaná 72 m²
        halo = ns.parse_detail(fx.DETAIL_HOUSE.replace("<p data-test-id=\"text\">Plocha domu:</p><p data-test-id=\"text\">150 m²</p>", "")
                               .replace("1 060 m²", "164 m²").replace("Zastavaná plocha:</p>", "Zastavaná plocha:</p><p data-test-id=\"text\">72 m²</p>"))
        self.assertIsNone(halo["house_area_m2"])
        self.assertEqual(halo["built_area_m2"], 72.0)
        self.assertEqual(halo["plot_area_m2"], 164.0)


def raw(pid="a", prop="pozemok", obec="Liptovská Lúžna", price=10000.0, area=500.0, title="Pozemok", desc="popis"):
    return {"source": "fake", "portal_id": pid, "url": f"https://x/{pid}", "title": title, "description_raw": desc,
            "prop_type": prop, "subtype": "Rekreačný pozemok", "obec": obec, "location": f"{obec}, okres Ružomberok",
            "area_m2": area, "price": price, "price_note": None, "price_per_m2": None, "main_photo_url": None}


class FilterTests(unittest.TestCase):
    def test_reject(self):
        self.assertIsNone(scraper.rejection_reason(raw()))
        self.assertIsNone(scraper.rejection_reason(raw(price=None)))
        bad = raw(); bad["location"] = "Ružomberok, okres Ružomberok"
        self.assertIn("iná obec", scraper.rejection_reason(bad))
        with mock.patch.object(config, "PRICE_MAX", 5000):
            self.assertIn("cena", scraper.rejection_reason(raw(price=10000)))
            self.assertIsNone(scraper.rejection_reason(raw(price=None)))   # bez ceny sa neodmieta
        with mock.patch.object(config, "MIN_PLOT_AREA_M2", 1000):
            self.assertIn("plocha", scraper.rejection_reason(raw(area=500)))
            self.assertIsNone(scraper.rejection_reason(raw(area=None)))
            self.assertIsNone(scraper.rejection_reason(raw(prop="dom", area=500)))


class PipelineTests(unittest.TestCase):
    def run_once(self, conn, raws, details=None):
        mod = mock.Mock(SOURCE_NAME="fake", LABEL="Fake", spec=["SOURCE_NAME", "LABEL", "fetch_all", "fetch_detail"])
        mod.fetch_all = lambda: [dict(r) for r in raws]
        mod.fetch_detail = lambda url: details or {"plot_area_m2": 726.0, "territory": "Intravilán", "utilities": None,
                                                    "house_area_m2": None, "ownership": None, "condition_label": None,
                                                    "description": "Pozemok sa dá rozdeliť podľa geometrického plánu. " * 3}
        pending = []
        scraper.process_source(mod, conn, pending)
        return pending

    def test_seed_new_drop_and_price_none(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.db")
            db.init_db(path)
            with db.connect(path) as conn:
                self.assertEqual(self.run_once(conn, [raw("a", price=10000)]), [])   # seed = ticho
                row = db.get_listing(conn, "fake:a")
                self.assertEqual(row["plot_area_m2"], 726.0)
                self.assertEqual(row["flags"], "split")
                p = self.run_once(conn, [raw("a", price=9000), raw("b", prop="dom", price=None)])
                self.assertEqual(sorted(x["kind"] for x in p), ["new", "price_drop"])
                # cena zmizla ("dohodou") -> posledná známa cena ostane, žiadne oznámenie
                p = self.run_once(conn, [raw("a", price=None), raw("b", prop="dom", price=None)])
                self.assertEqual(p, [])
                self.assertEqual(db.get_listing(conn, "fake:a")["price"], 9000.0)
                # cena sa vráti -> zmena
                p = self.run_once(conn, [raw("a", price=8000), raw("b", prop="dom", price=50000)])
                self.assertEqual(sorted(x["kind"] for x in p), ["price_drop", "price_set"])


class NotifyTests(unittest.TestCase):
    def item(self, **kw):
        l = raw(); l.update({"flags": "share", "plot_area_m2": 726.0, "territory": "Intravilán"}); l.update(kw)
        return {"kind": "new", "listing": l, "old_price": None}

    def test_embed(self):
        e = notify.build_embed(self.item())
        self.assertIn("10 000 €", e["description"])
        self.assertIn("726 m²", e["description"])
        self.assertIn("podiel / urbár", e["description"])
        e = notify.build_embed({"kind": "price_drop", "listing": raw(price=9000), "old_price": 10000.0})
        self.assertIn("~~10 000 €~~", e["description"])
        e = notify.build_embed(self.item(price=None, price_note="Cena dohodou"))
        self.assertIn("Cena dohodou", e["description"])

    def test_kinds(self):
        self.assertEqual(notify.kind_for("price_changed", None, 5000), "price_set")
        self.assertEqual(notify.kind_for("price_changed", 6000, 5000), "price_drop")
        self.assertIsNone(notify.kind_for("unchanged", 1, 1))

    def test_send(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("notify.requests.post") as p:
            self.assertEqual(notify.send_notifications([self.item()]), 0)
            p.assert_not_called()
        ok = mock.Mock(status_code=204)
        with mock.patch("notify.requests.post", return_value=ok) as p, mock.patch("notify.time.sleep"):
            self.assertEqual(notify.send_notifications([self.item() for _ in range(20)], webhook="https://h/w"),
                             config.NOTIFY_MAX_PER_RUN)
            self.assertEqual(p.call_count, 3)
        limited = mock.Mock(status_code=429); limited.json.return_value = {"retry_after": 0.1}
        with mock.patch("notify.requests.post", side_effect=[limited, ok]), mock.patch("notify.time.sleep"):
            self.assertEqual(notify.send_notifications([self.item()], webhook="https://h/w"), 1)
        bad = mock.Mock(status_code=500)
        with mock.patch("notify.requests.post", return_value=bad), mock.patch("notify.time.sleep"):
            self.assertEqual(notify.send_notifications([self.item()], webhook="https://h/w"), 0)


class RenderTests(unittest.TestCase):
    def build(self, raws):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "t.db")
        db.init_db(path)
        with db.connect(path) as conn:
            for r in raws:
                db.upsert_listing(conn, scraper.enrich(r))
            db.record_source_run(conn, "fake", "ok", len(raws), None)
        return render.render(path, os.path.join(d, "index.html"))

    def test_render(self):
        html = self.build([raw("a", title="<script>alert(1)</script>"), raw("b", prop="dom", price=None, obec="Liptovská Osada")])
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn('data-type="dom"', html)
        self.assertIn('data-type="pozemok"', html)
        self.assertIn("Cena neuvedená", html)
        self.assertIn('data-obec="Liptovská Osada"', html)
        self.assertIn("land-liptov-favs", html)
        self.assertIn("fav-btn", html)
        self.assertEqual(html.count('class="obec-btn'), 4)   # všetky + 3 obce

    def test_ppm2_label_says_what_it_refers_to(self):
        house = dict(raw("h", prop="dom", price=69900.0, area=None))
        house.update({"price_per_m2": None, "house_area_m2": None, "plot_area_m2": 164.0})
        self.assertEqual(render.ppm2_label(house), "426.22 €/m² pozemku")     # HALO: bez plochy domu -> jasný popisok
        self.assertEqual(render.sort_price_per_m2(house), 0)                  # do radenia sa nemieša s €/m² domu
        house["house_area_m2"] = 100.0
        self.assertEqual(render.ppm2_label(house), "699.00 €/m² domu")
        house["price_per_m2"] = 575.0                                         # hodnota z portálu má prednosť
        self.assertEqual(render.ppm2_label(house), "575.00 €/m²")
        plot = dict(raw("p", prop="pozemok", price=10000.0, area=500.0)); plot.update({"price_per_m2": None, "plot_area_m2": None})
        self.assertEqual(render.ppm2_label(plot), "20.00 €/m²")
        self.assertEqual(render.ppm2_label(dict(plot, price=None)), "")

    def test_migration_adds_built_area(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "old.db")
            import sqlite3
            conn = sqlite3.connect(path)
            conn.executescript(db.SCHEMA.replace("    built_area_m2     REAL,                  -- 'Zastavaná plocha' z detailu (pôdorys domu)\n", ""))
            cols = {r[1] for r in conn.execute("PRAGMA table_info(listings)")}
            self.assertNotIn("built_area_m2", cols)
            conn.close()
            db.init_db(path)
            with db.connect(path) as conn:
                self.assertIn("built_area_m2", {r["name"] for r in conn.execute("PRAGMA table_info(listings)")})

    def test_empty_db(self):
        html = self.build([])
        self.assertIn("Žiadne inzeráty", html)


if __name__ == "__main__":
    unittest.main()
