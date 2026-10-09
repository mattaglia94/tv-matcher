"""Elaborazione di un singolo ASIN: Amazon -> ricerca sui retailer -> scelta dei match.
Usato sia dall'exe/CLI (motore.py) sia dal runner del sito (web_runner.py)."""
import re

from regole import analizza, confronta_param, stesso_modello, unisci_parametri

ESITI = {"trovato": "Trovato", "non_presente": "Prodotto non presente",
         "nessun_simile": "Nessun modello simile", "errore": "Ricerca non riuscita",
         "saltato": "Saltato: modello Amazon mancante"}

AMAZON_DOMINIO = {"IT": "amazon.it", "DE": "amazon.de", "FR": "amazon.fr",
                  "ES": "amazon.es", "UK": "amazon.co.uk"}


def query_ricerca(info, P):
    """Testi di ricerca da provare sul retailer (dal più specifico al più largo)."""
    m, p, f = info.marca.title(), info.pollici, info.famiglia
    q = []
    if info.marca == "LG":
        if f.startswith("LG-OLED"):
            lettera = {"ENTRY": "B", "MID": "C", "PREMIUM": "G"}.get(f.split("-")[-1], "")
            q.append(f"LG OLED {p} {lettera}".strip())
        elif "QNED" in info.core:
            q.append(f"LG {p} QNED")
        elif "NANO" in info.core:
            q.append(f"LG {p} NANO")
        else:
            q.append(f"LG {p} UA7")
    elif info.marca == "HISENSE":
        serie = re.sub(r"^\d+", "", info.core)[:2]
        q.append(f"Hisense {p} {serie}{' PRO' if info.pro else ''}")
    elif info.marca == "SAMSUNG":
        t = {"NEOQLED": "Neo QLED", "MINILED": "Mini LED", "OLED": "OLED",
             "QLED": "QLED", "LED": "Crystal UHD"}.get(info.tecnologia, "")
        q.append(f"Samsung {p} {t}")
    elif m:
        q.append(f"{m} {p} {info.tecnologia.replace('MINILED', 'Mini LED')}".strip())
    if m:
        q.append(f"TV {m} {p}")
    if not P["stessa_marca"]["attivo"]:
        tec = {"MINILED": "Mini LED", "NEOQLED": "Mini LED"}.get(info.tecnologia, info.tecnologia)
        q.append(f"TV {p} {tec}".strip())
    return q


def info_dict(i):
    return {"marca": i.marca, "codice": i.codice, "pollici": i.pollici, "tecnologia": i.tecnologia,
            "famiglia": i.famiglia, "pro": i.pro, "risoluzione": i.risoluzione, "hz": i.hz,
            "anno": i.anno}


def riconosci_amazon(br, riga, anagrafica=None, log=print):
    """Ricava titolo/modello dell'ASIN. Ordine: modello scritto a mano -> anagrafica -> Amazon -> ricerca web.
    Ritorna (nome, modello, img, fonte, nota)."""
    paese = (riga.get("paese") or "IT").upper()
    nome, modello = riga.get("nome", ""), (riga.get("modello") or "").strip()
    if modello:
        return nome, modello, "", "inserito a mano", ""
    noto = (anagrafica or {}).get(f"{riga['asin']}|{paese}") or (anagrafica or {}).get(riga["asin"])
    if noto and noto.get("modello"):
        return noto.get("titolo", ""), noto["modello"], noto.get("img", ""), "anagrafica", ""
    a = br.amazon(riga["asin"], AMAZON_DOMINIO.get(paese, "amazon.it"))
    info = analizza(a["titolo"], a["modello"])
    if info.marca and info.pollici and info.codice:
        return a["titolo"], a["modello"] or info.codice, a.get("img", ""), "Amazon", ""
    # piano B: Amazon bloccato o pagina illeggibile -> motore di ricerca
    log(f"   Amazon non leggibile ({a['errore'] or 'modello non trovato'}): provo la ricerca web")
    try:
        titoli = br.cerca_web(riga["asin"])
    except Exception:
        titoli = []
    voti = {}
    for t in titoli:
        i = analizza(t)
        if i.marca and i.pollici and i.codice:
            k = (i.marca, i.core)
            voti.setdefault(k, [0, t, i.codice])[0] += 1
    if voti:
        _, t, cod = max(voti.values(), key=lambda v: v[0])
        return t, cod, a.get("img", ""), "ricerca web", "modello ricavato da ricerca web: verificare"
    return a["titolo"], a["modello"], a.get("img", ""), "", a["errore"] or "modello Amazon non riconosciuto"


def elabora_asin(br, riga, retailer, parametri, log=print, stop=lambda: False, anagrafica=None):
    """riga: {asin, paese, nome?, modello?}; retailer: [{nome, url}] del paese della riga.
    Ritorna dict con dati Amazon, match per retailer e righe di dettaglio."""
    P = unisci_parametri(parametri)
    paese = (riga.get("paese") or "IT").upper()
    out = {"asin": riga["asin"], "paese": paese, "amazon": {}, "match": {}, "esito": {}, "dettaglio": [], "errore": ""}
    url_amz = f"https://www.{AMAZON_DOMINIO.get(paese, 'amazon.it')}/dp/{riga['asin']}"
    nome, modello, img, fonte, nota = riconosci_amazon(br, riga, anagrafica, log)
    info = analizza(nome, modello)
    out["amazon"] = {"titolo": nome, "modello": info.codice or modello, "img": img, "url": url_amz,
                     "fonte": fonte, "nota": nota, **info_dict(info)}
    log(f"   Amazon ({fonte or 'non riconosciuto'}): {info.marca} {info.codice} {info.pollici}\" {info.famiglia}")
    if not info.marca or not info.pollici:
        out["errore"] = nota or "modello Amazon non riconosciuto"
        out["esito"] = {r["nome"]: "saltato" for r in retailer}
        log("   ⚠ modello Amazon non riconosciuto: scrivere il modello a mano")
        return out
    max_m = max(1, int(P.get("max_match") or 1))
    for r in retailer:
        if stop():
            break
        validi = {}
        pertinenti, ricerche_ok, errori = 0, 0, []
        for q in query_ricerca(info, P):
            url_s, links, stato = br.cerca(r["url"], q)
            # 404 su una pagina di ricerca = nessun risultato, non un errore
            if stato == "ok" or stato == "HTTP 404":
                ricerche_ok += 1
            else:
                errori.append(stato)
                out["dettaglio"].append({"retailer": r["nome"], "esito": f"ricerca: {stato}", "url": url_s, "ricerca": q})
            for l in links:
                c = analizza(l["testo"])
                if not c.marca or not c.pollici:
                    continue
                if c.marca == info.marca and c.pollici == info.pollici:
                    pertinenti += 1
                if P["stessa_marca"]["attivo"] and c.marca != info.marca:
                    continue
                ok, motivo, score = confronta_param(info, c, P)
                out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "famiglia": c.famiglia,
                                         "pollici": c.pollici, "anno": c.anno, "url": l["url"],
                                         "esito": ("VALIDO " if ok else "scartato: ") + motivo, "ricerca": q})
                if ok and l["url"] not in validi:
                    validi[l["url"]] = (score, c, l.get("img", ""), motivo)
            if len(validi) >= max_m:
                break
        scelti, codici = [], set()
        for url, (score, c, im, motivo) in sorted(validi.items(), key=lambda x: x[1][0]):
            nome_pag = ""
            if len(scelti) >= max_m:
                break
            if c.codice in codici:
                continue
            if P.get("verifica_url", True):
                vivo, titolo_pag, corpo, og = br.verifica(url)
                if not vivo:
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url, "esito": "URL non attivo"})
                    continue
                cp = analizza(titolo_pag)
                if cp.codice and cp.pollici and P["pollici"]["attivo"] and \
                        abs(cp.pollici - info.pollici) > int(P["pollici"].get("tolleranza") or 0):
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": "pagina prodotto non coerente"})
                    continue
                full = analizza(f"{titolo_pag} {corpo[:20000]}", c.codice)
                mancanti = [n for k, n in (("dolby_vision", "Dolby Vision"), ("hdr10plus", "HDR10+"),
                                           ("hdmi21", "HDMI 2.1"))
                            if P[k]["attivo"] and getattr(info, k) and not getattr(full, k)]
                if mancanti:
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": "scartato: manca " + ", ".join(mancanti)})
                    continue
                if full.anno and P["anno"]["attivo"] and full.anno != int(P["anno"]["valore"]):
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": f"scartato: anno {full.anno} (da pagina)"})
                    continue
                if full.anno:
                    motivo = "ok"
                im = og or im
                nome_pag = titolo_pag.strip()
                # il codice sulla pagina prodotto è il più affidabile: se c'è, vince
                if cp.codice and cp.marca == c.marca and cp.pollici == c.pollici and not stesso_modello(info, cp):
                    c.codice = cp.codice
            codici.add(c.codice)
            scelti.append({"modello": c.codice, "url": url, "img": im, "nota": "" if motivo == "ok" else motivo,
                           "titolo": (nome_pag or c.testo)[:160], **info_dict(c)})
        out["match"][r["nome"]] = scelti
        if scelti:
            esito = "trovato"
        elif pertinenti:
            esito = "nessun_simile"
        elif ricerche_ok:
            esito = "non_presente"
        else:
            esito = "errore"
        out["esito"][r["nome"]] = esito
        testo = ", ".join(s["modello"] for s in scelti) or ESITI[esito]
        if esito == "errore" and errori:
            testo += f" ({errori[-1]})"
        log(f"   {r['nome']}: {testo}")
    return out
