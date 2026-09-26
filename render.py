"""
Vygeneruje statickú HTML stránku (docs/index.html) z dát v SQLite. Publikuje sa cez GitHub Pages.
Všetky texty z inzerátov sa escapujú (html.escape).
"""

import html
from datetime import datetime, timezone

import config
import db

SOURCE_LABELS = {"nehnutelnosti_sk": "nehnutelnosti.sk"}
TYPE_LABELS = {"pozemok": "Pozemok", "dom": "Dom / chata"}
FLAG_LABELS = {
    "share": ("Podiel / urbár", "Predáva sa podiel (urbárske / spoluvlastnícke pozemky), nie samostatná parcela"),
    "split": ("Delený pozemok", "Popis spomína delenie / odčlenenie / geometrický plán - over rozsah parcely"),
    "half_house": ("Polovica domu", "V titulku je polovica domu / dvojdomu"),
}
UTIL_LABELS = {"voda": "voda", "elektrina": "elektrina", "plyn": "plyn", "kanalizacia": "kanalizácia"}


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt_eur(value) -> str:
    return f"{value:,.0f} €".replace(",", " ")


def fmt_m2(value) -> str:
    return f"{value:,.0f} m²".replace(",", " ")


def category(card: dict) -> str:
    return "removed" if card["status"] != "active" else card["prop_type"]


def price_html(card: dict) -> str:
    if card["price"] is None:
        return f'<div class="card-price dim">{esc(card.get("price_note") or "Cena neuvedená")}</div>'
    return f'<div class="card-price">{fmt_eur(card["price"])}</div>'


def price_trend_html(history: list[dict]) -> str:
    prices = [h["price"] for h in history if h["price"] is not None]
    if len(prices) <= 1:
        return ""
    css = "price-down" if prices[-1] < prices[0] else ("price-up" if prices[-1] > prices[0] else "")
    arrow = "↓" if css == "price-down" else ("↑" if css == "price-up" else "→")
    chain = " → ".join(f"{p:,.0f}".replace(",", " ") for p in prices)
    return f'<div class="price-history {css}">{arrow} história: {chain} €</div>'


def util_text(utilities: str | None) -> str:
    """'voda=Nedostupné;elektrina=Verejná' -> 'voda: Nedostupné · elektrina: Verejná'."""
    parts = []
    for item in (utilities or "").split(";"):
        key, _, val = item.partition("=")
        if key in UTIL_LABELS and val:
            parts.append(f"{UTIL_LABELS[key]}: {val}")
    return " · ".join(parts)


def sort_price_per_m2(card: dict) -> float:
    if card.get("price_per_m2"):
        return card["price_per_m2"]
    area = card.get("plot_area_m2") or card.get("area_m2")
    return card["price"] / area if card["price"] and area else 0


def card_html(card: dict, history: list[dict], seed_day: str | None = None) -> str:
    first = datetime.fromisoformat(card["first_seen_at"])
    age_days = (datetime.now(timezone.utc) - first).days
    ppm2 = sort_price_per_m2(card)

    badges = []
    if card["status"] != "active":
        badges.append('<span class="badge badge-sold">Stiahnuté z ponuky</span>')
    elif age_days <= config.NEW_BADGE_DAYS and card["first_seen_at"][:10] != seed_day:
        badges.append('<span class="badge badge-fresh">NOVÉ</span>')
    badges.append(f'<span class="badge badge-type-{esc(card["prop_type"])}">'
                  f'{esc(card.get("subtype") or TYPE_LABELS.get(card["prop_type"], "?"))}</span>')
    for flag in (card.get("flags") or "").split(","):
        if flag in FLAG_LABELS:
            label, tip = FLAG_LABELS[flag]
            badges.append(f'<span class="badge badge-flag" title="{esc(tip)}">{label}</span>')
    if card.get("territory"):
        badges.append(f'<span class="badge badge-info">{esc(card["territory"])}</span>')
    if card.get("condition_label"):
        badges.append(f'<span class="badge badge-info">{esc(card["condition_label"])}</span>')

    photo = card["main_photo_url"]
    if photo:
        photo_html = (f'<img class="card-photo" src="{esc(photo)}" alt="" loading="lazy" referrerpolicy="no-referrer" '
                      f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';">'
                      f'<div class="card-photo card-photo-placeholder" style="display:none;">Bez fotky</div>')
    else:
        photo_html = '<div class="card-photo card-photo-placeholder">Bez fotky</div>'

    meta = [esc(card["obec"])]
    if card["prop_type"] == "pozemok":
        area = card.get("plot_area_m2") or card.get("area_m2")
        if area:
            meta.append(fmt_m2(area))
    else:
        if card.get("house_area_m2"):
            meta.append(f'dom {fmt_m2(card["house_area_m2"])}')
        if card.get("plot_area_m2"):
            meta.append(f'pozemok {fmt_m2(card["plot_area_m2"])}')
        if not card.get("house_area_m2") and not card.get("plot_area_m2") and card.get("area_m2"):
            meta.append(fmt_m2(card["area_m2"]))
    if ppm2:
        meta.append(f"{ppm2:,.2f} €/m²".replace(",", " "))
    util = util_text(card.get("utilities"))
    util_html = f'<div class="card-meta">Siete: {esc(util)}</div>' if util else ""
    area_sort = card.get("plot_area_m2") or card.get("area_m2") or 0
    src = SOURCE_LABELS.get(card["source"], card["source"])

    return f"""
    <div class="card" data-cat="{category(card)}" data-type="{esc(card['prop_type'])}" data-obec="{esc(card['obec'])}" data-pid="{esc(card['portal_id'])}"
         data-price="{card['price'] or 0:.0f}" data-ppm2="{ppm2:.2f}" data-area="{area_sort}" data-first="{int(first.timestamp())}">
      <button type="button" class="fav-btn" title="Pridať do obľúbených" aria-label="Pridať do obľúbených" aria-pressed="false">☆</button>
      <a href="{esc(card['url'])}" target="_blank" rel="noopener" class="card-photo-link">{photo_html}</a>
      <div class="card-body">
        <div class="badges">{''.join(badges)}</div>
        <a href="{esc(card['url'])}" target="_blank" rel="noopener" class="card-title">{esc(card['title'])}</a>
        {price_html(card)}
        {price_trend_html(history)}
        <div class="card-meta">{' · '.join(meta)}</div>
        {util_html}
        <div class="card-footer">
          <span class="source-tag"><a href="{esc(card['url'])}" target="_blank" rel="noopener">{esc(src)}</a></span>
          <span class="dates">od {card['first_seen_at'][:10]} · naposledy {card['last_seen_at'][:10]}</span>
        </div>
      </div>
    </div>"""


def run_status_html(runs: dict[str, dict]) -> str:
    if not runs:
        return ""
    parts, problem = [], False
    for source, label in SOURCE_LABELS.items():
        run = runs.get(source)
        if not run:
            parts.append(f"{label}: zatiaľ neprebehol")
        elif run["status"] == "ok":
            parts.append(f'{label}: OK ({run["found"]} inzerátov, {run["run_at"][:16].replace("T", " ")} UTC)')
        else:
            problem = True
            parts.append(f'<b>{label}: ZLYHALO ({esc(run["status"])})</b> - {esc((run["message"] or "")[:200])}'
                         f' ({run["run_at"][:16].replace("T", " ")} UTC)')
    css = "run-status run-problem" if problem else "run-status"
    prefix = "⚠️ Posledný beh zlyhal - dáta môžu byť neaktuálne. " if problem else ""
    return f'<div class="{css}">{prefix}{" · ".join(parts)}</div>'


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pozemky a domy Liptov - monitor</title>
<style>
  :root { --bg:#0f1115; --card-bg:#1a1d24; --border:#2a2e38; --text:#e8eaed; --text-dim:#9aa0aa;
          --accent:#4f9dff; --green:#3ecf8e; --red:#ff5c5c; --yellow:#f5c518; }
  * { box-sizing: border-box; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,"Segoe UI",Roboto,sans-serif; margin:0; padding:16px; }
  h1 { font-size:20px; margin:0 0 4px; }
  .subtitle { color:var(--text-dim); font-size:13px; margin-bottom:12px; }
  .run-status { font-size:12px; color:var(--text-dim); margin-bottom:12px; }
  .run-problem { color:#fff; background:rgba(255,92,92,.18); border:1px solid var(--red); border-radius:6px; padding:8px 10px; }
  .controls { display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap; align-items:center; }
  .controls button { background:var(--card-bg); border:1px solid var(--border); color:var(--text); padding:6px 12px; border-radius:6px; cursor:pointer; font-size:13px; }
  .controls button.active, .controls button.sort-btn-active { background:var(--accent); border-color:var(--accent); color:#fff; }
  .sort-label { color:var(--text-dim); font-size:13px; }
  .controls button.obec-btn.active { background:var(--accent); border-color:var(--accent); color:#fff; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:14px; }
  .card { background:var(--card-bg); border:1px solid var(--border); border-radius:10px; overflow:hidden; display:flex; flex-direction:column; }
  .card { position:relative; }
  .card[data-cat="removed"] { opacity:.5; }
  .fav-btn { position:absolute; top:8px; right:8px; z-index:2; width:34px; height:34px; border-radius:50%; border:none; cursor:pointer;
             background:rgba(15,17,21,.7); color:#fff; font-size:20px; line-height:34px; padding:0; }
  .fav-btn:hover { background:rgba(15,17,21,.9); }
  .fav-btn.on { color:var(--yellow); }
  .card.is-fav { border-color:var(--yellow); }
  .card-photo-link { display:block; }
  .card-photo { width:100%; height:170px; object-fit:cover; background:#000; display:block; }
  .card-photo-placeholder { align-items:center; justify-content:center; color:var(--text-dim); font-size:12px; background:#15171c; display:flex; }
  .card-body { padding:12px; display:flex; flex-direction:column; gap:6px; }
  .badges { display:flex; gap:4px; flex-wrap:wrap; }
  .badge { font-size:10px; padding:2px 6px; border-radius:4px; font-weight:600; }
  .badge-fresh { background:var(--green); color:#000; }
  .badge-sold { background:var(--red); color:#fff; }
  .badge-type-pozemok { background:#1f4d3a; color:#8ff0c0; }
  .badge-type-dom { background:#2a3f5f; color:#9dc4ff; }
  .badge-flag { background:#4a3a1a; color:#f0c070; }
  .badge-info { background:#2a2e38; color:var(--text-dim); }
  .badge-warn { background:var(--yellow); color:#000; }
  .card-title { color:var(--text); font-weight:600; font-size:14px; text-decoration:none; line-height:1.3; }
  .card-title:hover { color:var(--accent); }
  .card-price { font-size:20px; font-weight:700; }
  .card-price.dim { font-size:16px; color:var(--text-dim); font-weight:600; }
  .plus { font-size:12px; font-weight:500; color:var(--yellow); }
  .plus.ok { color:var(--green); } .plus.dim { color:var(--text-dim); }
  .total-note { font-size:12px; color:var(--yellow); margin-top:-4px; }
  .price-history { font-size:11px; color:var(--text-dim); }
  .price-history.price-down { color:var(--green); } .price-history.price-up { color:var(--red); }
  .card-meta { font-size:12px; color:var(--text-dim); }
  .card-footer { display:flex; justify-content:space-between; gap:8px; flex-wrap:wrap; font-size:10px; color:var(--text-dim); margin-top:4px; border-top:1px solid var(--border); padding-top:6px; }
  .card-footer a { color:var(--accent); }
  .empty-state { color:var(--text-dim); padding:40px; text-align:center; }
</style>
</head>
<body>
  <h1>🌲 Pozemky a domy · Liptov</h1>
  <div class="subtitle">Aktualizované: %%UPDATED%% · %%OBCE%% · predaj</div>
  %%RUN_STATUS%%
  <div class="controls">
    <button class="filter-btn active" data-filter="all" data-label="Všetky aktívne">Všetky aktívne (%%N_ALL%%)</button>
    <button class="filter-btn" data-filter="pozemok" data-label="Pozemky">Pozemky (%%N_POZEMOK%%)</button>
    <button class="filter-btn" data-filter="dom" data-label="Domy / chaty">Domy / chaty (%%N_DOM%%)</button>
    <button class="filter-btn" data-filter="fav" data-label="★ Obľúbené">★ Obľúbené (0)</button>
    <button class="filter-btn" data-filter="removed" data-label="Stiahnuté">Stiahnuté (%%N_REMOVED%%)</button>
  </div>
  <div class="controls">
    <span class="sort-label">Obec:</span>
    %%OBEC_BUTTONS%%
  </div>
  <div class="controls">
    <span class="sort-label">Zoradiť:</span>
    <button class="sort-btn sort-btn-active" data-field="price">Cena</button>
    <button class="sort-btn" data-field="ppm2">€/m²</button>
    <button class="sort-btn" data-field="area">Plocha</button>
    <button class="sort-btn" data-field="first">Najnovšie</button>
  </div>
  <div id="grid" class="grid">
    %%CARDS%%
  </div>
  <div id="empty" class="empty-state" style="display:none;">Žiadne inzeráty v tomto filtri.</div>

<script>
  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  const cards = Array.from(grid.children);
  let currentFilter = 'all';
  let currentObec = 'all';
  const sortState = { field: 'price', asc: true };
  const DEFAULT_ASC = { price: true, ppm2: true, area: false, first: false };

  // Obľúbené: ukladajú sa len v tomto prehliadači (localStorage), kľúčom je ID inzerátu.
  const FAV_KEY = 'land-liptov-favs';
  let favs = new Set();
  try { favs = new Set(JSON.parse(localStorage.getItem(FAV_KEY) || '[]')); } catch (e) {}
  const saveFavs = () => { try { localStorage.setItem(FAV_KEY, JSON.stringify([...favs])); } catch (e) {} };
  const isFav = c => favs.has(c.dataset.pid);
  function paintFavs() {
    cards.forEach(c => {
      const on = isFav(c), b = c.querySelector('.fav-btn');
      b.textContent = on ? '★' : '☆';
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.title = on ? 'Odstrániť z obľúbených' : 'Pridať do obľúbených';
      c.classList.toggle('is-fav', on);
    });
  }

  const active = c => c.dataset.cat !== 'removed';
  const catOk = (c, f) => f === 'fav' ? isFav(c) : (f === 'removed' ? !active(c)
      : (active(c) && (f === 'all' || c.dataset.type === f)));
  const obecOk = (c, o) => o === 'all' || c.dataset.obec === o;

  function updateCounts() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
      const n = cards.filter(c => catOk(c, btn.dataset.filter) && obecOk(c, currentObec)).length;
      btn.textContent = btn.dataset.label + ' (' + n + ')';
    });
    document.querySelectorAll('.obec-btn').forEach(btn => {
      const n = cards.filter(c => catOk(c, currentFilter) && obecOk(c, btn.dataset.obec)).length;
      btn.textContent = btn.dataset.label + ' (' + n + ')';
    });
  }

  function applyFilter() {
    let visible = 0;
    cards.forEach(c => {
      const show = catOk(c, currentFilter) && obecOk(c, currentObec);
      c.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    empty.style.display = visible === 0 ? 'block' : 'none';
    updateCounts();
  }

  function applySort() {
    const value = c => parseFloat(c.dataset[sortState.field]) || 0;
    cards.slice().sort((a, b) => {
      const fa = isFav(a), fb = isFav(b);
      if (fa !== fb) return fa ? -1 : 1;          // obľúbené vždy na začiatku
      const va = value(a), vb = value(b);
      if (sortState.asc && (va === 0 || vb === 0) && va !== vb) return va === 0 ? 1 : -1;  // bez údaja na koniec
      return sortState.asc ? va - vb : vb - va;
    }).forEach(c => grid.appendChild(c));
  }

  function updateSortLabels() {
    document.querySelectorAll('.sort-btn').forEach(btn => {
      const on = btn.dataset.field === sortState.field;
      btn.classList.toggle('sort-btn-active', on);
      btn.textContent = btn.textContent.replace(/ [↑↓]$/, '') + (on ? (sortState.asc ? ' ↑' : ' ↓') : '');
    });
  }

  document.querySelectorAll('.filter-btn').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    applyFilter();
  }));

  grid.addEventListener('click', e => {
    const b = e.target.closest('.fav-btn');
    if (!b) return;
    const c = b.closest('.card');
    if (favs.has(c.dataset.pid)) favs.delete(c.dataset.pid); else favs.add(c.dataset.pid);
    saveFavs(); paintFavs(); applySort(); applyFilter();
  });

  document.querySelectorAll('.obec-btn').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.obec-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentObec = btn.dataset.obec;
    applyFilter();
  }));

  document.querySelectorAll('.sort-btn').forEach(btn => btn.addEventListener('click', () => {
    if (sortState.field === btn.dataset.field) sortState.asc = !sortState.asc;
    else { sortState.field = btn.dataset.field; sortState.asc = DEFAULT_ASC[btn.dataset.field]; }
    updateSortLabels(); applySort();
  }));

  paintFavs(); updateSortLabels(); applySort(); applyFilter();
</script>
</body>
</html>
"""


def obec_buttons_html(cards: list[dict]) -> str:
    buttons = [f'<button class="obec-btn active" data-obec="all" data-label="Všetky obce">Všetky obce ({len(cards)})</button>']
    for _, label in config.OBCE:
        n = sum(1 for c in cards if c["obec"] == label)
        buttons.append(f'<button class="obec-btn" data-obec="{esc(label)}" data-label="{esc(label)}">{esc(label)} ({n})</button>')
    return "\n    ".join(buttons)


def render(db_path: str | None = None, output_path: str | None = None) -> str:
    db_path = db_path or config.DB_PATH
    output_path = output_path or config.OUTPUT_HTML_PATH
    with db.connect(db_path) as conn:
        cards = db.get_all_listings(conn)
        seed_day = min((r["first_seen_at"][:10] for r in cards), default=None)
        histories = {c["id"]: db.get_price_history(conn, c["id"]) for c in cards}
        runs = db.last_source_runs(conn)

    cards.sort(key=lambda c: (c["price"] is None, c["price"] or 0))
    counts = {"pozemok": 0, "dom": 0, "removed": 0}
    for c in cards:
        counts[category(c)] += 1

    page = (PAGE_TEMPLATE
            .replace("%%UPDATED%%", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
            .replace("%%OBCE%%", esc(", ".join(label for _, label in config.OBCE)))
            .replace("%%RUN_STATUS%%", run_status_html(runs))
            .replace("%%OBEC_BUTTONS%%", obec_buttons_html(cards))
            .replace("%%N_POZEMOK%%", str(counts["pozemok"])).replace("%%N_DOM%%", str(counts["dom"]))
            .replace("%%N_REMOVED%%", str(counts["removed"]))
            .replace("%%N_ALL%%", str(counts["pozemok"] + counts["dom"]))
            .replace("%%CARDS%%", "\n".join(card_html(c, histories[c["id"]], seed_day) for c in cards)))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Vygenerované: {output_path} ({len(cards)} kariet: {counts})")
    return page


if __name__ == "__main__":
    render()
