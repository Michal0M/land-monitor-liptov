"""
Nastavenia monitora pozemkov a domov v Liptove (Liptovská Lúžna, Liptovská Osada, Liptovské Revúce).
Uprav tento súbor, keď chceš pridať obec, zúžiť cenu alebo zmeniť správanie scrapera.
"""

# --- Čo hľadáme ---
# (slug na nehnutelnosti.sk, názov obce). Slug = časť URL, napr. /vysledky/pozemky/<slug>/predaj.
# Ďalšiu obec pridáš riadkom sem - slug zistíš z URL po vyhľadaní obce na nehnutelnosti.sk.
OBCE = [
    ("liptovska-luzna", "Liptovská Lúžna"),
    ("liptovska-osada", "Liptovská Osada"),
    ("liptovske-revuce", "Liptovské Revúce"),
]
# Kategórie na portáli: pozemok = všetky druhy pozemkov (lesy, rekreačné, stavebné, ornú pôdu...), dom = domy/chaty/chalupy.
KATEGORIE = [("pozemky", "pozemok"), ("domy", "dom")]

# Tvrdé filtre (None = bez limitu). Inzerát mimo limitov sa z DB vymaže. Inzerát BEZ ceny ("Cena dohodou")
# alebo bez plochy sa nikdy neodmieta - radšej ho vidieť.
PRICE_MAX = None                 # € (celková cena)
MIN_PLOT_AREA_M2 = None          # min. plocha (m²) pri pozemkoch podľa výpisu

# --- Zdroj ---
BASE_NEHNUTELNOSTI = "https://www.nehnutelnosti.sk"
NEHNUTELNOSTI_URL = BASE_NEHNUTELNOSTI + "/vysledky/{cat}/{obec}/predaj"

# --- Technické nastavenia scrapera ---
REQUEST_DELAY_SECONDS = 4
REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = "Mozilla/5.0 (compatible; land-monitor-liptov/1.0; osobne pouzitie, 1 beh denne)"
PAGE_SIZE = 30                   # nehnutelnosti.sk dáva 30 inzerátov na stranu
MAX_PAGES_PER_QUERY = 5

DETAIL_REFRESH_DAYS = 14         # detail (plocha pozemku, siete, celý popis) sa obnovuje raz za N dní
DETAIL_MAX_PER_RUN = 60
DETAIL_VERSION = 1               # zvýš, ak detail začne poskytovať nové údaje - cache sa jednorazovo obnoví

NEW_BADGE_DAYS = 3               # "NOVÉ" badge; pri úplne prvom behu sa nezobrazuje

DB_PATH = "data/listings.db"
OUTPUT_HTML_PATH = "docs/index.html"

# --- Discord oznámenia (webhook v GitHub Secret DISCORD_WEBHOOK_POZEMKY) ---
NOTIFY_MAX_PER_RUN = 15          # ochrana pred zaplavením kanála
