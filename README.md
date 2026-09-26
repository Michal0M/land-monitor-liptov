# Monitor pozemkov a domov · Liptov

Denný scraper (GitHub Actions) → SQLite s históriou cien → statická stránka na GitHub Pages + oznámenia na Discord.
Rovnaká architektúra ako `rental-monitor-bb`.

**Obce:** Liptovská Lúžna, Liptovská Osada, Liptovské Revúce (ďalšie pridáš v `config.py` → `OBCE`).
**Čo:** predaj pozemkov (všetky druhy vrátane lesov, rekreačných a stavebných, vrátane delených) a domov/chát.
**Zdroj:** nehnutelnosti.sk (overené 26.9.2026, výpis je v surovom HTML, netreba JavaScript).

## Nasadenie (jednorazovo)
1. Nový repozitár na GitHube (napr. `land-monitor-liptov`), nahraj obsah tohto priečinka.
2. Settings → Pages → Source: `main` / `/docs`.
3. Settings → Actions → General → Workflow permissions: **Read and write**.
4. Discord: kanál `#nehnuteľnosti-ll-lo-lr` → ozubené koliesko → Integrácie → Webhooky → Nový webhook → skopíruj URL.
5. GitHub: Settings → Secrets and variables → Actions → New repository secret `DISCORD_WEBHOOK_POZEMKY` = URL webhooku. **URL nikam inam nevkladaj.**
6. Actions → „Denný scrape pozemkov a domov Liptov" → Run workflow (s políčkom „Poslať testovaciu správu na Discord" na test).

## Ako to funguje
- Každá kombinácia kategória (`pozemky`, `domy`) × obec je jeden dopyt `/vysledky/<kategoria>/<obec>/predaj`. Obec bez inzerátov je platný výsledok (nula kariet), nie chyba; stránka sa overuje cez `<h1>` (ochrana pred presmerovaním na zoznam za celé Slovensko).
- **Detail inzerátu** (len nové/zastarané, cache 14 dní): plocha pozemku a domu, územie (intravilán/extravilán), vlastníctvo, siete (voda/elektrina/plyn/kanalizácia), stav domu, celý popis.
- **Príznaky z popisu** (badge na karte): *Podiel / urbár* (predáva sa podiel v spoločenstve, nie samostatná parcela), *Delený pozemok* (popis spomína delenie, odčlenenie, geometrický plán), *Polovica domu*. Sú to odhady z textu, nie fakty - over v inzeráte.
- Inzerát **bez ceny** („Cena dohodou") sa nikdy neodmieta; zobrazí sa bez ceny a radí sa na koniec. Keď sa cena neskôr objaví, príde oznámenie „Cena zverejnená".
- Tvrdé filtre v `config.py` (`PRICE_MAX`, `MIN_PLOT_AREA_M2`) sú predvolene vypnuté (None). Nič sa nemaže, kým ich nezapneš.
- Inzerát, ktorý zmizol z portálu, ostane v záložke **Stiahnuté**; označuje sa len po úplnom úspešnom behu.

## Stránka
Záložky: Všetky aktívne / Pozemky / Domy-chaty / ★ Obľúbené / Stiahnuté. Filter podľa obce, radenie (cena, €/m², plocha, najnovšie). **Obľúbené** (hviezdička) sa ukladajú len v tomto prehliadači a zariadení (localStorage) a sú vždy na začiatku.

## Discord oznámenia
Nový inzerát, zľava, zvýšená cena, cena zverejnená, opäť v ponuke. Prvý beh je tichý (seed). Max 15 oznámení za beh. Chyba Discordu scraper nezhodí.

## Testy
`python -m unittest discover -s tests -v` (beží aj v každom behu workflowu pred scrapovaním).

## Keď to prestane fungovať
- Červený pruh v stránke / červený workflow = zdroj zlyhal (blokovanie, zmena štruktúry) – pozri log kroku „Spustiť scraper".
- Nový slug obce zistíš z URL po vyhľadaní obce na nehnutelnosti.sk (`/vysledky/pozemky/<slug>/predaj`). Kategórie `chaty-chalupy` a `stavebne-pozemky` s obcou v URL nefungujú (presmerujú na celé Slovensko).
- Portál je len jeden; ďalšie zdroje (reality.sk, topreality.sk) sa dajú pridať ako modul rovnako ako v rental-monitore.
