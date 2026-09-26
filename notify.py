"""
Oznámenia na Discord cez webhook (kanál #nehnuteľnosti-ll-lo-lr).

Webhook URL je TAJOMSTVO: berie sa iba z premennej prostredia DISCORD_WEBHOOK_POZEMKY (GitHub Secret),
nikdy z kódu. Chyba pri odosielaní NIKDY neukončí scraper - len sa vypíše do logu.
"""

import os
import time

import requests

import config

SECRET_ENV = "DISCORD_WEBHOOK_POZEMKY"
COLORS = {"new": 0x2ECC71, "price_drop": 0xF1C40F, "price_up": 0xE67E22, "price_set": 0x9B59B6, "reappeared": 0x3498DB}
HEADINGS = {"new": "🆕 Nový inzerát", "price_drop": "📉 Zľava", "price_up": "📈 Zvýšená cena",
            "price_set": "💶 Cena zverejnená", "reappeared": "🔁 Opäť v ponuke"}
TYPE_EMOJI = {"pozemok": "🌲", "dom": "🏠"}
FLAG_TEXT = {"share": "podiel / urbár", "split": "delený pozemok", "half_house": "polovica domu"}


def kind_for(result: str, old_price, new_price) -> str | None:
    """Zmapuje výsledok upsertu na druh oznámenia (None = neoznamovať)."""
    if result == "new":
        return "new"
    if result == "reappeared":
        return "reappeared"
    if result == "price_changed" and new_price is not None:
        if old_price is None:
            return "price_set"
        return "price_drop" if new_price < old_price else "price_up"
    return None


def fmt_eur(v) -> str:
    return f"{v:,.0f} €".replace(",", " ")


def fmt_m2(v) -> str:
    return f"{v:,.0f} m²".replace(",", " ")


def build_embed(item: dict) -> dict:
    l, kind = item["listing"], item["kind"]
    if l.get("price") is None:
        price = l.get("price_note") or "Cena neuvedená"
    elif kind in ("price_drop", "price_up") and item.get("old_price"):
        price = f"~~{fmt_eur(item['old_price'])}~~ → **{fmt_eur(l['price'])}**"
    else:
        price = f"**{fmt_eur(l['price'])}**"
    facts = [l.get("obec") or "?", l.get("subtype") or ("Pozemok" if l["prop_type"] == "pozemok" else "Dom")]
    if l["prop_type"] == "pozemok" and (l.get("plot_area_m2") or l.get("area_m2")):
        facts.append(fmt_m2(l.get("plot_area_m2") or l["area_m2"]))
    elif l["prop_type"] == "dom":
        if l.get("house_area_m2"):
            facts.append(f"dom {fmt_m2(l['house_area_m2'])}")
        if l.get("plot_area_m2"):
            facts.append(f"pozemok {fmt_m2(l['plot_area_m2'])}")
        if not l.get("house_area_m2") and not l.get("plot_area_m2") and l.get("area_m2"):
            facts.append(fmt_m2(l["area_m2"]))
    if l.get("price_per_m2"):
        facts.append(f"{l['price_per_m2']:,.2f} €/m²".replace(",", " "))
    if l.get("territory"):
        facts.append(l["territory"])
    flags = [FLAG_TEXT[f] for f in (l.get("flags") or "").split(",") if f in FLAG_TEXT]
    lines = [f"{HEADINGS[kind]} {TYPE_EMOJI.get(l['prop_type'], '')}", price, " · ".join(facts)]
    if flags:
        lines.append("⚠️ " + ", ".join(flags))
    embed = {"title": (l.get("title") or "Inzerát")[:250], "url": l["url"],
             "description": "\n".join(lines), "color": COLORS[kind]}
    if l.get("main_photo_url"):
        embed["thumbnail"] = {"url": l["main_photo_url"]}
    return embed


def _post(url: str, payload: dict) -> bool:
    for _ in range(3):
        try:
            r = requests.post(url, json=payload, timeout=15)
        except requests.RequestException as e:
            print(f"[notify] chyba siete: {type(e).__name__}")  # bez URL, aby sa tajomstvo nedostalo do logu
            return False
        if r.status_code == 429:
            try:
                wait = float(r.json().get("retry_after", 2))
            except Exception:
                wait = 2
            time.sleep(min(wait, 30) + 0.5)
            continue
        if r.status_code >= 300:
            print(f"[notify] Discord vrátil HTTP {r.status_code}")
            return False
        return True
    return False


def send_notifications(items: list[dict], webhook: str | None = None) -> int:
    """Pošle oznámenia (po 5 embedov v správe, max NOTIFY_MAX_PER_RUN). Vracia počet odoslaných."""
    webhook = webhook or os.environ.get(SECRET_ENV)
    if not items:
        return 0
    if not webhook:
        print(f"[notify] {len(items)} oznámení preskočených - chýba premenná {SECRET_ENV}")
        return 0
    shown = items[:config.NOTIFY_MAX_PER_RUN]
    sent = 0
    for i in range(0, len(shown), 5):
        chunk = shown[i:i + 5]
        payload = {"username": "Pozemky Liptov", "embeds": [build_embed(x) for x in chunk]}
        if i == 0 and len(items) > len(shown):
            payload["content"] = f"Dnes {len(items)} zmien, zobrazených prvých {len(shown)} - zvyšok na stránke."
        if _post(webhook, payload):
            sent += len(chunk)
        time.sleep(1)
    print(f"[notify] odoslaných {sent}/{len(items)} oznámení")
    return sent


def send_test(webhook: str | None = None) -> bool:
    webhook = webhook or os.environ.get(SECRET_ENV)
    if not webhook:
        print(f"Chýba premenná {SECRET_ENV}")
        return False
    return _post(webhook, {"username": "Pozemky Liptov",
                           "content": "✅ Testovacia správa: Discord notifikácie pre pozemky fungujú."})


if __name__ == "__main__":
    import sys
    sys.exit(0 if send_test() else 1)
