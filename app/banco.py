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
                     r"protector|schutz|monitor|proiettore|beamer|projector|ricambio|ersatz|replacement|stand|piedistallo|"
                     r"standfuß|pied", re.I)

JS_RISULTATI = r"""
() => [...document.querySelectorAll('div[data-component-type="s-search-result"][data-asin]')].map(d => ({
  asin: d.getAttribute('data-asin'),
  titolo: (d.querySelector('h2') || {}).innerText || '',
  prezzo: (d.querySelector('.a-price .a-offscreen') || {}).innerText || '',
  sponsor: !!d.querySelector('.puis-sponsored-label-text, .s-sponsored-label-text')
})).filter(x => x.asin)
"""


def raccogli(paese, per_marca=5):
    from browser import Browser
    from regole import trova_marca, trova_pollici_testo as trova_pollici
    from web_runner import Pubblicatore, assicura_branch, leggi_json, REPO, TOKEN
    dom = DOMINIO[paese]
    br = Browser(visibile=False)
    visti, scelti = set(), []
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
                q = urllib.parse.quote_plus(f"{marca} " + PAROLA[paese].format(p=p))
                br._vai(f"https://www.{dom}/s?k={q}")
                br._pausa()
                try:
                    righe = br.page.evaluate(JS_RISULTATI)
                except Exception:
                    righe = []
                print(f"{paese} {marca} {p}\": {len(righe)} risultati", flush=True)
                in_questa = 0
                for r in righe:
                    t = r["titolo"].strip()
                    if r["asin"] in visti or not t or ESCLUDI.search(t):
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
        Pubblicatore(f"banco/asin_{paese}.json").salva(scelti, forza=True)
    os.makedirs("output", exist_ok=True)
    json.dump(scelti, open(f"output/asin_{paese}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "raccogli":
        raccogli(sys.argv[2].upper())
