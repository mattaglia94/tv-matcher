"""Elaborazione di un singolo ASIN: Amazon -> ricerca sui retailer -> scelta dei match.
Usato sia dall'exe/CLI (motore.py) sia dal runner del sito (web_runner.py)."""
import re

from regole import analizza, confronta_param, leggi_prezzo, stesso_modello, unisci_parametri

ESITI = {"trovato": "Trovato", "non_presente": "Prodotto non presente",
         "nessun_simile": "Nessun modello simile", "errore": "Ricerca non riuscita",
         "illeggibile": "Risultati non leggibili",
         "saltato": "Saltato: modello Amazon mancante"}

# indirizzi di ricerca vecchi o sbagliati salvati nelle impostazioni -> indirizzo corretto
URL_CORRETTI = {"https://www.expert.it/search?q={q}": "https://www.expert.it/it/it/exp/shop/search?terms={q}"}

PID_MARCHE = {"SAM": "SAMSUNG", "XIA": "XIAOMI", "LGE": "LG", "HIS": "HISENSE", "TCL": "TCL", "PHI": "PHILIPS",
              "SON": "SONY", "PAN": "PANASONIC", "SHA": "SHARP", "TOS": "TOSHIBA", "HAI": "HAIER", "SAB": "SABA"}

IDEALO = {"IT": "idealo.it", "DE": "idealo.de", "FR": "idealo.fr", "ES": "idealo.es", "UK": "idealo.co.uk"}

AMAZON_DOMINIO = {"IT": "amazon.it", "DE": "amazon.de", "FR": "amazon.fr",
                  "ES": "amazon.es", "UK": "amazon.co.uk"}


NOMI_TEC = {"MINILED": "Mini LED", "NEOQLED": "Mini LED", "QLED": "QLED", "OLED": "OLED", "LED": "4K"}
MARCHE_PRINCIPALI = ["Samsung", "LG", "Hisense", "TCL", "Philips", "Sony", "Xiaomi"]


def query_ricerca(info, P):
    """Testi di ricerca da provare sul retailer (dal più specifico al più largo)."""
    m, p, f = info.marca.title(), info.pollici, info.famiglia
    tec = NOMI_TEC.get(info.tecnologia, "")
    if P.get("modalita") == "concorrente":
        q = [f"TV {p} {tec}".strip(), f"TV {p} pollici"]
        # poi le marche concorrenti più diffuse, finché non si trova un match
        q += [f"{x} {p} {tec}".strip() for x in MARCHE_PRINCIPALI if x.upper() != info.marca][:3]
        return q
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
    return q


def chiave_negozio(nome):
    """'Euronics-DE' -> 'euronics', 'El Corte Inglés' -> 'elcorteingles', 'AO.com' -> 'ao'."""
    n = re.sub(r"-(IT|DE|FR|ES|UK)$", "", nome.strip(), flags=re.I).lower()
    n = n.replace("é", "e").replace("è", "e").replace(".com", "").replace(".fr", "")
    return re.sub(r"[^a-z0-9]", "", n)


def ponte_idealo(br, info, r, P, paese, out, max_m, log=print):
    """Il sito del retailer non è leggibile: cerca su idealo i modelli simili e tiene solo
    le offerte di quel retailer. Ogni match riporta 'via' = dominio idealo usato."""
    dom = IDEALO.get(paese)
    chiave = chiave_negozio(r["nome"])
    if not dom or len(chiave) < 3:
        return []
    concorrente = P["modalita"] == "concorrente"
    candidati = {}
    for q in query_ricerca(info, P):
        try:
            prodotti = br.idealo_cerca(dom, q)
        except Exception:
            prodotti = []
        for l in prodotti:
            c = analizza(l["testo"])
            if not c.marca or not c.pollici or (c.marca != info.marca) != concorrente:
                continue
            ok, motivo, score = confronta_param(info, c, P)
            if ok and l["url"] not in candidati:
                candidati[l["url"]] = (score, c, motivo)
        if len(candidati) >= 3:
            break
    scelti, codici = [], set()
    for url, (score, c, motivo) in sorted(candidati.items(), key=lambda x: x[1][0])[:5]:
        if len(scelti) >= max_m:
            break
        if c.codice in codici:
            continue
        try:
            offerte = br.idealo_offerte(url)
        except Exception:
            offerte = []
        off = next((o for o in offerte if chiave in re.sub(r"[^a-z0-9]", "", o["negozio"].lower())), None)
        out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "famiglia": c.famiglia, "pollici": c.pollici,
                                 "anno": c.anno, "url": url, "ricerca": f"{dom}",
                                 "esito": (f"VALIDO via {dom}: offerta {r['nome']} {off.get('prezzo', '')}".strip() if off
                                           else f"via {dom}: nessuna offerta {r['nome']} ({len(offerte)} offerte)")})
        if not off:
            continue
        codici.add(c.codice)
        nota = f"trovato tramite {dom}: il sito di {r['nome']} non era leggibile"
        if motivo != "ok":
            nota += f"; {motivo}"
        scelti.append({"modello": c.codice, "url": off["url"], "img": off.get("img", ""), "nota": nota,
                       "titolo": (off.get("testo") or c.testo)[:160], "via": dom, "prezzo": off.get("prezzo", ""),
                       "pagina_comparatore": url, **info_dict(c)})
    return scelti


def info_dict(i):
    return {"marca": i.marca, "codice": i.codice, "pollici": i.pollici, "tecnologia": i.tecnologia,
            "famiglia": i.famiglia, "fascia": i.fascia, "pro": i.pro, "risoluzione": i.risoluzione, "hz": i.hz,
            "anno": i.anno}


def riconosci_amazon(br, riga, anagrafica=None, log=print):
    """Ricava i dati dell'ASIN. Ordine: modello scritto a mano -> anagrafica -> Amazon -> ricerca web.
    Ritorna dict: titolo, modello, img, fonte, nota, marca, prezzo."""
    paese = (riga.get("paese") or "IT").upper()
    nome, modello = riga.get("nome", ""), (riga.get("modello") or "").strip()
    noto = (anagrafica or {}).get(f"{riga['asin']}|{paese}") or (anagrafica or {}).get(riga["asin"]) or {}
    vuoto = {"titolo": nome or noto.get("titolo", ""), "modello": "", "img": noto.get("img", ""), "fonte": "", "nota": "",
             "marca": riga.get("marca", "") or noto.get("marca", ""), "prezzo": ""}

    def basta(titolo, mod, marca):
        """Il TV è riconoscibile? Serve marca, diagonale e codice (o tecnologia + fascia).
        Un modello come "F PRO 32" da solo non dice la marca: allora serve anche il titolo."""
        i = analizza(titolo, mod, marca)
        return bool(i.marca and i.pollici and (i.codice or (i.tecnologia and i.fascia)))

    if modello and basta(vuoto["titolo"], modello, vuoto["marca"]):
        return {**vuoto, "modello": modello, "fonte": "inserito a mano"}
    if noto.get("modello") and not modello and basta(noto.get("titolo", ""), noto["modello"], noto.get("marca", "")):
        return {**vuoto, "modello": noto["modello"], "fonte": "anagrafica"}
    if modello:
        log(f"   modello '{modello}' non basta a riconoscere il TV: leggo anche la pagina Amazon")
    a = br.amazon(riga["asin"], AMAZON_DOMINIO.get(paese, "amazon.it"))
    if modello and not a["modello"]:
        a = {**a, "modello": modello}  # il modello scritto a mano resta, il titolo Amazon aggiunge marca e diagonale
    dati = {**vuoto, "titolo": a["titolo"] or vuoto["titolo"], "modello": a["modello"], "img": a.get("img", "") or vuoto["img"],
            "marca": a.get("marca", "") or vuoto["marca"], "prezzo": a.get("prezzo", "")}
    info = analizza(dati["titolo"], a["modello"], dati["marca"], leggi_prezzo(dati["prezzo"]))
    if info.marca and info.pollici and info.codice:
        return {**dati, "modello": a["modello"] or info.codice, "fonte": "Amazon"}
    if info.marca and info.pollici and info.tecnologia and info.fascia:
        # modello non in archivio (marca o serie nuova): si procede con i dati letti da Amazon
        nota = "modello non in archivio: dati ricavati dalla pagina Amazon"
        if info.fascia_fonte == "stimata":
            nota += f", fascia stimata dal prezzo ({dati['prezzo']})"
        return {**dati, "fonte": "Amazon", "nota": nota}
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
        return {**dati, "titolo": t, "modello": cod, "fonte": "ricerca web", "nota": "modello ricavato da ricerca web: verificare"}
    return {**dati, "nota": a["errore"] or "modello Amazon non riconosciuto"}


def elabora_asin(br, riga, retailer, parametri, log=print, stop=lambda: False, anagrafica=None):
    """riga: {asin, paese, nome?, modello?}; retailer: [{nome, url}] del paese della riga.
    Ritorna dict con dati Amazon, match per retailer e righe di dettaglio."""
    P = unisci_parametri(parametri)
    concorrente = P["modalita"] == "concorrente"
    paese = (riga.get("paese") or "IT").upper()
    out = {"asin": riga["asin"], "paese": paese, "amazon": {}, "match": {}, "esito": {}, "dettaglio": [], "errore": ""}
    url_amz = f"https://www.{AMAZON_DOMINIO.get(paese, 'amazon.it')}/dp/{riga['asin']}"
    am = riconosci_amazon(br, riga, anagrafica, log)
    nome, modello, fonte, nota = am["titolo"], am["modello"], am["fonte"], am["nota"]
    info = analizza(nome, modello, am.get("marca", ""), leggi_prezzo(am.get("prezzo", "")))
    out["amazon"] = {"titolo": nome, "modello": info.codice or modello, "img": am["img"], "url": url_amz,
                     "fonte": fonte, "nota": nota, "marca_amazon": am.get("marca", ""), "prezzo": am.get("prezzo", ""),
                     "fascia_fonte": info.fascia_fonte, "marca_nuova": info.marca_nuova, "regola": info.regola,
                     **info_dict(info)}
    log(f"   Amazon ({fonte or 'non riconosciuto'}): {info.marca} {info.codice} {info.pollici}\" {info.famiglia}")
    # per cercare un concorrente servono tecnologia e fascia dell'ASIN, altrimenti il confronto è casuale
    non_classificato = P["modalita"] == "concorrente" and not (info.tecnologia and info.fascia)
    if not info.marca or not info.pollici or non_classificato:
        out["errore"] = nota or ("fascia del modello Amazon non riconosciuta" if non_classificato else "modello Amazon non riconosciuto")
        out["esito"] = {r["nome"]: "saltato" for r in retailer}
        log("   ⚠ modello Amazon non riconosciuto: scrivere il modello a mano")
        return out
    max_m = max(1, int(P.get("max_match") or 1))
    out["ponte"] = {}
    for r in retailer:
        r = {**r, "url": URL_CORRETTI.get(r["url"], r["url"])}
        if stop():
            break
        validi = {}
        pertinenti, ricerche_ok, errori, tv_letti = 0, 0, [], 0
        for q in query_ricerca(info, P):
            url_s, links, stato = br.cerca(r["url"], q)
            # 404 su una pagina di ricerca = nessun risultato, non un errore
            if stato == "ok" or stato == "HTTP 404":
                ricerche_ok += 1
            else:
                errori.append(stato)
                out["dettaglio"].append({"retailer": r["nome"], "esito": f"ricerca: {stato}", "url": url_s, "ricerca": q})
            for l in links:
                if l["url"].split("?")[0] == url_s.split("?")[0]:
                    continue  # filtri della pagina di ricerca (marca, prezzo...), non prodotti
                c = analizza(l["testo"])
                if not c.codice:
                    # molti retailer mettono il codice modello solo nell'indirizzo (es. _tcl-75t69c-..., pidSAMQE75QN70H)
                    # Unieuro: pid + 3 lettere della marca (pidSAMQE75QN70H, pidXIA50APRO2)
                    slug = l["url"].split("?")[0].rsplit("/", 1)[-1]
                    slug = re.sub(r"pid([A-Z]{3})", lambda m: f" {PID_MARCHE.get(m.group(1), '')} " + ("XIA" if m.group(1) == "XIA" else ""), slug)
                    c2 = analizza(f"{l['testo']} {re.sub(r'[-_.]+', ' ', slug)}")
                    if c2.codice and (not c.marca or c2.marca == c.marca) and (not c.pollici or c2.pollici == c.pollici):
                        c = c2
                if not c.marca or not c.pollici:
                    continue
                tv_letti += 1
                if (c.marca != info.marca) == concorrente:
                    if c.pollici == info.pollici:
                        pertinenti += 1
                else:
                    continue  # stessa marca in modalità concorrente, o altra marca in modalità stessa marca
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
                # anno e risoluzione SOLO da titolo/intestazione del prodotto: il resto della pagina
                # contiene menu, banner, copyright ed etichette energetiche con altri anni e risoluzioni
                ris_pag = cp.risoluzione
                if P["risoluzione"]["attivo"] and info.risoluzione and ris_pag and ris_pag != info.risoluzione and \
                        not (P["modalita"] == "concorrente" and {ris_pag, info.risoluzione} <= {"HD", "FHD"}):
                    mancanti.append(f"risoluzione {info.risoluzione} (pagina: {ris_pag})")
                if mancanti:
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": "scartato: manca " + ", ".join(mancanti)})
                    continue
                anno_pag = cp.anno or c.anno
                if anno_pag and P["anno"]["attivo"] and anno_pag != int(P["anno"]["valore"]):
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": f"scartato: anno {anno_pag} (da pagina)"})
                    continue
                if anno_pag:  # anno letto nel titolo della pagina: non è più "da verificare"
                    motivo = ", ".join(x for x in motivo.split(", ") if x != "anno da verificare") or "ok"
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
        elif ricerche_ok and tv_letti:
            esito = "non_presente"
        elif ricerche_ok:
            # pagina caricata ma nessun TV riconoscibile: quasi sempre blocco anti-bot o pagina dinamica
            esito = "illeggibile"
        else:
            esito = "errore"
        if esito in ("errore", "illeggibile") and P.get("ponte_idealo", True) and not stop():
            log(f"   {r['nome']}: sito non leggibile, provo tramite {IDEALO.get(paese, 'comparatore')}")
            via = ponte_idealo(br, info, r, P, paese, out, max_m, log)
            out["ponte"][r["nome"]] = IDEALO.get(paese, "")
            if via:
                scelti = via
                out["match"][r["nome"]] = scelti
                esito = "trovato"
        out["esito"][r["nome"]] = esito
        testo = ", ".join(s["modello"] + (f" (via {s['via']})" if s.get("via") else "") for s in scelti) or ESITI[esito]
        if esito == "errore" and errori:
            testo += f" ({errori[-1]})"
        log(f"   {r['nome']}: {testo}")
    return out
