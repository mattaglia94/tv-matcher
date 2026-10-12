"""Banco di prova del motore (non usato dal sito).

  python app/banco.py raccogli IT     -> pesca da Amazon IT TV dei brand principali (40-75") e ne legge la scheda
                                        salva banco/asin_IT.json nel branch `dati`
  python app/banco.py valuta FILE...  -> (offline) confronta ciò che il motore capisce dal titolo
                                        con la scheda tecnica di Amazon e stampa gli errori
"""
import json
import os
import random
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DOMINIO = {"IT": "amazon.it", "DE": "amazon.de", "FR": "amazon.fr", "ES": "amazon.es", "UK": "amazon.co.uk"}
PAROLA = {"IT": "tv {p} pollici", "DE": "fernseher {p} zoll", "FR": "tv {p} pouces", "ES": "tv {p} pulgadas", "UK": "tv {p} inch"}
MARCHE = {
    "IT": ["Samsung", "LG", "Sony", "Philips", "TCL", "Hisense", "Xiaomi", "Panasonic", "Telefunken", "Sharp"],
    "DE": ["Samsung", "LG", "Sony", "Philips", "TCL", "Hisense", "Xiaomi", "Panasonic", "Grundig", "Telefunken"],
    "FR": ["Samsung", "LG", "Sony", "Philips", "TCL", "Hisense", "Xiaomi", "Panasonic", "Thomson", "Toshiba"],
    "ES": ["Samsung", "LG", "Sony", "Philips", "TCL", "Hisense", "Xiaomi", "Panasonic", "Sharp", "Toshiba"],
    "UK": ["Samsung", "LG", "Sony", "Philips", "TCL", "Hisense", "Xiaomi", "Panasonic", "Toshiba", "Sharp"],
}
POLLICI = [43, 50, 55, 65, 75]
ESCLUDI = re.compile(r"halterung|staffa|supporto|soporte|support mural|wall mount|bracket|telecomando|fernbedienung|"
                     r"remote|télécommande|mando|cavo|kabel|cable|câble|cover|custodia|stick|soundbar|barra de sonido|"
                     r"protector|schutz|\bmonitor\b|proiettore|beamer|projector|ricambio|ersatz|replacement|\bstand\b|piedistallo|"
                     r"standfuß|\bpied\b|\bpieds\b|tira de led|strip led|led strip|barre|bande|rétroéclairage|retroillumin|backlight|hintergrundbeleucht|retroilumin", re.I)

JS_RISULTATI = r"""
() => [...document.querySelectorAll('div[data-component-type="s-search-result"][data-asin]')].map(d => ({
  asin: d.getAttribute('data-asin'),
  titolo: ((d.querySelector('[data-cy="title-recipe"]') || d.querySelector('h2') || {}).innerText
          || ((d.querySelector('h2') || {getAttribute: () => ''}).getAttribute('aria-label')) || '').replace(/\s+/g, ' '),
  prezzo: (d.querySelector('.a-price .a-offscreen') || {}).innerText || '',
  sponsor: !!d.querySelector('.puis-sponsored-label-text, .s-sponsored-label-text')
})).filter(x => x.asin)
"""


def cerca_amazon(br, dom, testo, pagina=1):
    url = f"https://www.{dom}/s?k={urllib.parse.quote_plus(testo)}" + (f"&page={pagina}" if pagina > 1 else "")
    for tentativo in range(3):
        br._vai(url)
        br._pausa()
        if br._amazon_continua():
            br._vai(url)
        try:
            righe = br.page.evaluate(JS_RISULTATI)
        except Exception:
            righe = []
        if righe:
            return righe
        time.sleep(random.uniform(5, 10))
    return []


def cerca_motore(br, dom, testo):
    """Piano B: Amazon blocca le ricerche dai server, i motori di ricerca no. Prende i link /dp/<ASIN>."""
    righe, visti = [], set()
    for url in (f"https://www.bing.com/search?q={urllib.parse.quote_plus('site:' + dom + ' ' + testo)}&count=30",
                f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus('site:' + dom + ' ' + testo)}"):
        try:
            br._vai(url)
            br._pausa(1, 2)
            link = br.page.evaluate("""() => [...document.querySelectorAll('a[href]')].map(a => [a.href, a.innerText])""")
        except Exception:
            continue
        for href, tit in link:
            href = urllib.parse.unquote(href)
            m = re.search(r"amazon\.[a-z.]+/(?:[^\s\"]*?/)?(?:dp|gp/product)/([A-Z0-9]{10})", href)
            if m and m.group(1) not in visti and len(tit.strip()) > 15:
                visti.add(m.group(1))
                righe.append({"asin": m.group(1), "titolo": tit.strip().split("\n")[0], "prezzo": "", "fonte": "motore"})
        if righe:
            break
    return righe


def raccogli(paese, per_marca=5, lotto=""):
    from browser import Browser
    from regole import catalogo_predefinito, e_accessorio, imposta_catalogo, trova_marca, trova_pollici_testo as trova_pollici
    imposta_catalogo(catalogo_predefinito())
    from web_runner import Pubblicatore, assicura_branch, leggi_json, REPO, TOKEN
    dom = DOMINIO[paese]
    br = Browser(visibile=False)
    visti, scelti, diario = set(), [], []
    if lotto:  # lotto nuovo: niente ASIN già nel banco, risultati della seconda pagina
        try:
            visti |= {x["asin"] for x in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "banco_campioni.json")))}
        except Exception:
            pass
        random.seed(f"{paese}{lotto}")
    try:
        br._vai(f"https://www.{dom}/")
        br._pausa(2, 4)
        for marca in MARCHE[paese]:
            presi = 0
            pollici = POLLICI[:]
            random.shuffle(pollici)
            for p in pollici[:3]:
                if presi >= per_marca:
                    break
                testo = f"{marca} " + PAROLA[paese].format(p=p)
                righe = cerca_amazon(br, dom, testo, pagina=2 if lotto else 1) or cerca_motore(br, dom, testo)
                print(f"{paese} {marca} {p}\": {len(righe)} risultati", flush=True)
                if len(diario) < 400:
                    try:
                        tit = br.page.title()
                        corpo = br.page.inner_text("body")[:300] if not righe else ""
                    except Exception:
                        tit, corpo = "?", ""
                    diario.append({"marca": marca, "pollici": p, "url": br.page.url, "titolo_pagina": tit,
                                   "risultati": len(righe), "corpo": corpo,
                                   "titoli": [x["titolo"][:90] for x in righe[:6]]})
                in_questa = 0
                for r in righe:
                    t = r["titolo"].strip()
                    if r["asin"] in visti or not t or ESCLUDI.search(t) or e_accessorio(t):
                        continue
                    pp = trova_pollici(t)
                    if not pp or not 40 <= pp <= 75:
                        continue
                    m = trova_marca(t)
                    if not m or m.lower() != marca.lower():
                        continue
                    visti.add(r["asin"])
                    scelti.append({"asin": r["asin"], "paese": paese, "marca_cercata": marca, "titolo_ricerca": t,
                                   "prezzo_ricerca": r["prezzo"]})
                    presi += 1
                    in_questa += 1
                    if presi >= per_marca or in_questa >= 2:
                        break
        print(f"{paese}: {len(scelti)} ASIN, ora leggo le schede", flush=True)
        for i, s in enumerate(scelti, 1):
            a = br.amazon(s["asin"], dom)
            s.update({k: a.get(k, "") for k in ("titolo", "modello", "marca", "prezzo", "img", "errore")})
            s["scheda"] = a.get("scheda") or {}
            print(f"  [{i}/{len(scelti)}] {s['asin']} {s['modello'] or '-'} | {len(s['scheda'])} voci | {s['errore']}", flush=True)
    finally:
        br.chiudi()
    if REPO and TOKEN:
        assicura_branch()
        suff = f"_{lotto}" if lotto else ""
        Pubblicatore(f"banco/asin_{paese}{suff}.json").salva(scelti, forza=True)
        Pubblicatore(f"banco/diario_{paese}{suff}.json").salva(diario, forza=True)
    os.makedirs("output", exist_ok=True)
    json.dump(scelti, open(f"output/asin_{paese}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def valuta(file, dettaglio=True):
    """Ciò che il motore ricava dal SOLO titolo, confrontato con la scheda tecnica di Amazon (verità di riferimento)."""
    from collections import Counter
    from regole import analizza, leggi_prezzo, leggi_scheda, trova_marca
    righe = []
    for f in file:
        righe += json.load(open(f, encoding="utf-8"))
    righe = [r for r in righe if r.get("titolo")]
    campi = ("marca", "pollici", "risoluzione", "tecnologia", "hz", "anno")
    ok, ko, manca, verif = Counter(), Counter(), Counter(), Counter()
    fonti, errori = Counter(), []
    for r in righe:
        info = analizza(r["titolo"], "", "", leggi_prezzo(r.get("prezzo") or r.get("prezzo_ricerca") or ""))
        sch = leggi_scheda({k.lower(): v for k, v in (r.get("scheda") or {}).items()})
        sch.setdefault("marca", trova_marca(r.get("marca") or "") or r.get("marca_cercata", "").upper())
        fonti[info.fascia_fonte or "-"] += 1
        for c in campi:
            vero, mio = sch.get(c), getattr(info, c)
            if c == "marca":
                vero = trova_marca(str(vero or "")) or str(vero or "").upper()
            if not vero:
                continue
            verif[c] += 1
            if not mio:
                manca[c] += 1
                errori.append((r["paese"], r["asin"], c, "manca", vero, r["titolo"][:110]))
            elif str(mio).upper() != str(vero).upper() and not (c == "tecnologia" and {mio, vero} <= {"MINILED", "NEOQLED"}):
                ko[c] += 1
                errori.append((r["paese"], r["asin"], c, mio, vero, r["titolo"][:110]))
            else:
                ok[c] += 1
    print(f"{len(righe)} TV lette")
    for c in campi:
        n = verif[c] or 1
        print(f"  {c:12} giusti {ok[c]:3}/{verif[c]:3} ({100*ok[c]//n}%)  sbagliati {ko[c]:3}  non letti {manca[c]:3}")
    print("  fascia da:", dict(fonti))
    if dettaglio:
        for e in sorted(errori, key=lambda x: (x[2], x[0])):
            print(" ", *e[:5], "|", e[5])
    return ok, ko, manca, errori


def esiti(file):
    """Statistiche dei run di confronto: per negozio esiti, motivi di scarto, scarti sospetti da controllare."""
    from collections import Counter, defaultdict
    per_neg = defaultdict(Counter)
    motivi = Counter()
    sospetti = []
    n_asin = 0
    for f in file:
        st = json.load(open(f, encoding="utf-8"))
        for r in st.get("risultati", []):
            n_asin += 1
            am = r.get("amazon", {})
            for neg, e in (r.get("esito") or {}).items():
                per_neg[f"{r['paese']} {neg}"][e] += 1
            for d in r.get("dettaglio", []):
                e = d.get("esito", "")
                if e.startswith(("errore", "illeggibile", "bloccato")) or "errore" in e[:30]:
                    motivi["NEGOZIO " + d.get("retailer", "") + ": " + e[:90]] += 1
                if e.startswith("scartato"):
                    m = re.sub(r"[\d.,]+", "#", e.split("(")[0])[:60]
                    motivi[m] += 1
                    if d.get("pollici") == am.get("pollici") and not re.search(r"pollici|stesso modello|marca|tecnologia|fascia|anno 20", e):
                        sospetti.append((r["asin"], am.get("codice") or am.get("modello"), d["retailer"], d.get("modello"), e[:120], d.get("url", "")[:110]))
    print(f"{n_asin} ASIN")
    for neg, c in sorted(per_neg.items()):
        tot = sum(c.values())
        print(f"  {neg:28} trovati {c.get('trovato', 0) + c.get('ok', 0):3}/{tot:3}  ", dict(c))
    print("motivi di scarto:")
    for m, n in motivi.most_common(25):
        print(f"  {n:4}  {m}")
    print(f"scarti da controllare (stessi pollici): {len(sospetti)}")
    for s_ in sospetti[:80]:
        print(" ", *s_)


def sonda(urls):
    """Apre pagine problematiche e salva cosa vede il browser (titolo, stato, link, testo) per capire come leggerle."""
    from browser import Browser, JS_LINKS
    from web_runner import Pubblicatore, REPO, TOKEN
    br = Browser(visibile=False)
    out = []
    try:
        for u in urls:
            br.riscalda(u)
            r = br._vai(u)
            time.sleep(4)
            try:
                links = br.page.evaluate(JS_LINKS)
            except Exception as e:
                links = [{"href": "ERR", "testo": str(e)}]
            try:
                corpo = br.page.inner_text("body")[:1500]
                html = br.page.content()
            except Exception:
                corpo, html = "", ""
            prod = [l for l in links if re.search(r"\d{2}", l.get("testo", "")) and len(l.get("testo", "")) > 25][:40]
            try:  # link con immagini (loghi dei negozi) e attributi utili per capire la struttura delle offerte
                extra = br.page.evaluate("""() => [...document.querySelectorAll('a[href]')].filter(a => /£|€|store|shop|go/i.test(a.innerText + a.href))
                    .slice(0, 40).map(a => ({href: a.href, testo: a.innerText.replace(/\\s+/g,' ').slice(0,200),
                    alt: [...a.querySelectorAll('img')].map(i => i.alt).join('/'), aria: a.getAttribute('aria-label') || '',
                    padre: (a.closest('li,article,[class*=offer i],[data-testid]') || {}).className || ''}))""")
            except Exception as e:
                extra = [str(e)]
            out.append({"url": u, "finale": br.page.url, "stato": getattr(r, "status", None), "titolo": br.page.title(),
                        "n_link": len(links), "link_prodotto": prod, "extra": extra, "corpo": corpo,
                        "html_len": len(html), "html_prodotti": [m.group(0)[:300] for m in re.finditer(r"<[^>]+(product|tile|card)[^>]*>", html, re.I)][:10]})
            print(u, out[-1]["stato"], out[-1]["titolo"][:60], len(links), len(prod), flush=True)
    finally:
        br.chiudi()
    if REPO and TOKEN:
        Pubblicatore("banco/sonda.json").salva(out, forza=True)


if __name__ == "__main__":
    if sys.argv[1] == "raccogli":
        raccogli(sys.argv[2].upper(), lotto=os.environ.get("LOTTO", ""))
    elif sys.argv[1] == "sonda":
        sonda(json.loads(os.environ.get("URLS") or "[]") or sys.argv[2:])
    elif sys.argv[1] == "esiti":
        esiti(sys.argv[2:])
    elif sys.argv[1] == "valuta":
        valuta(sys.argv[2:])
