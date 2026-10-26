"""Elaborazione di un singolo ASIN: Amazon -> ricerca sui retailer -> scelta dei match.
Usato sia dall'exe/CLI (motore.py) sia dal runner del sito (web_runner.py)."""
import re

from regole import _cod_norm, _tec_equivalenti, analizza, anno_obiettivo, confronta_identico, stesso_modello_esatto, e_accessorio, arricchisci, classe_hz, hz_diverse, confronta_param, leggi_prezzo, leggi_scheda, stesso_modello, unisci_parametri

ESITI = {"trovato": "Trovato", "non_presente": "Prodotto non presente",
         "nessun_simile": "Nessun modello simile", "errore": "Ricerca non riuscita",
         "illeggibile": "Sito non consultabile",
         "saltato": "Saltato: modello Amazon mancante"}

# indirizzi di ricerca vecchi o sbagliati salvati nelle impostazioni -> indirizzo corretto
GIORNI_ARCHIVIO_AMAZON = 20  # una pagina Amazon letta da meno di 20 giorni si riusa (stessi dati, più veloce)

URL_CORRETTI = {  # indirizzi di ricerca cambiati dai negozi (vale anche per le configurazioni salvate dal sito)
    "https://www.expert.it/search?q={q}": "https://www.expert.it/it/it/exp/shop/search?terms={q}",
    "https://www.joybuy.de/search?keyword={q}": "https://www.joybuy.de/s?k={q}",
    "https://www.joybuy.fr/search?keyword={q}": "https://www.joybuy.fr/s?k={q}",
    "https://www.joybuy.co.uk/search?keyword={q}": "https://www.joybuy.co.uk/s?k={q}",
    "https://www.elcorteingles.es/search-nwx/1/?s={q}": "https://www.elcorteingles.es/search-nwx/?s={q}",
}

PID_MARCHE = {"SAM": "SAMSUNG", "XIA": "XIAOMI", "LGE": "LG", "HIS": "HISENSE", "TCL": "TCL", "PHI": "PHILIPS",
              "SON": "SONY", "PAN": "PANASONIC", "SHA": "SHARP", "TOS": "TOSHIBA", "HAI": "HAIER", "SAB": "SABA"}

IDEALO = {"IT": "idealo.it", "DE": "idealo.de", "FR": "idealo.fr", "ES": "idealo.es"}
# comparatore usato come ponte quando il sito del negozio non si legge: idealo, nel Regno Unito PriceRunner
COMPARATORE = {**IDEALO, "UK": "pricerunner.com"}

AMAZON_DOMINIO = {"IT": "amazon.it", "DE": "amazon.de", "FR": "amazon.fr",
                  "ES": "amazon.es", "UK": "amazon.co.uk"}


NOMI_TEC = {"MINILED": "Mini LED", "NEOQLED": "Mini LED", "QLED": "QLED", "OLED": "OLED", "LED": "4K"}
MARCHE_PRINCIPALI = ["Samsung", "LG", "Hisense", "TCL", "Philips", "Sony", "Xiaomi"]


def query_ricerca(info, P):
    """Testi di ricerca da provare sul retailer (dal più specifico al più largo)."""
    m, p, f = info.marca.title(), info.pollici, info.famiglia
    tec = NOMI_TEC.get(info.tecnologia, "")
    if P.get("ricerca") == "identico":
        # stesso modello: si cerca il codice (intero e senza suffissi di paese/canale), poi marca + codice
        cod = re.sub(r"\.[A-Z]{2,4}$", "", (info.codice or "").upper()).strip()
        q = [cod] if cod else []
        n = cod.replace("-", "").replace(" ", "")
        if info.core and info.core in n:
            corto = n[:n.index(info.core) + len(info.core)]
            if corto != n:
                q.append(corto)
        if cod and m and m.upper() not in cod:
            q.append(f"{m} {cod}")
        if info.marca == "XIAOMI" and info.chiave and p:  # i negozi scrivono "Xiaomi TV F Pro 43", non L43MB-FPEU
            q.insert(0, f"Xiaomi {info.chiave.split('-')[0]}{' Pro' if info.pro else ''} {p}")
        if not q and m and p:
            q.append(f"{m} {p}")
        return list(dict.fromkeys(q))
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


_ANNI_IDEALO = {}


def anno_da_idealo(br, c, paese, log=print):
    """Anno di un modello che né il titolo né la scheda riportano: lo cerca su idealo.
    Lo stesso nome commerciale (es. "A Pro 75") esiste in più anni: vale solo un prodotto idealo
    la cui pagina riporta ESATTAMENTE il codice modello (es. L75MB-APEU). Altrimenti l'anno resta sconosciuto."""
    dom = IDEALO.get(paese)
    if not dom or not hasattr(br, "idealo_cerca"):
        return None
    chiave = (dom, c.codice)
    if chiave in _ANNI_IDEALO:
        return _ANNI_IDEALO[chiave]
    noto = br.cache_get(f"anno:{dom}:{c.codice}") if hasattr(br, "cache_get") else None
    if noto:
        return noto.get("anno")
    cod = re.sub(r"[^A-Z0-9]", "", c.codice.upper())
    anno = None
    try:
        visti = 0
        for l in br.idealo_cerca(dom, c.codice)[:12]:
            i = analizza(l["testo"])
            if not (i.anno and i.marca == c.marca and i.pollici == c.pollici):
                continue
            if cod in re.sub(r"[^A-Z0-9]", "", l["testo"].upper()):
                anno = i.anno
                break
            if visti >= 3:
                continue
            visti += 1  # il codice non è nel nome: lo cerco nella pagina del prodotto su idealo
            vivo, titolo, corpo, _ = br.verifica(l["url"])[:4]
            if vivo and cod in re.sub(r"[^A-Z0-9]", "", f"{titolo} {corpo}".upper()):
                anno = i.anno
                break
    except Exception:
        anno = None
    _ANNI_IDEALO[chiave] = anno
    if anno and hasattr(br, "cache_put"):
        br.cache_put(f"anno:{dom}:{c.codice}", {"anno": anno})
    return anno


def ponte_idealo(br, info, r, P, paese, out, max_m, log=print):
    """Il sito del retailer non è leggibile: cerca su idealo i modelli simili e tiene solo
    le offerte di quel retailer. Ogni match riporta 'via' = dominio idealo usato."""
    dom = COMPARATORE.get(paese)
    chiave = chiave_negozio(r["nome"])
    if not dom or len(chiave) < 2:
        return []
    pr = dom == "pricerunner.com"
    cerca = (lambda q: br.pricerunner_cerca(q)) if pr else (lambda q: br.idealo_cerca(dom, q))
    offerte_di = (lambda u: br.pricerunner_offerte(u)) if pr else (lambda u: br.idealo_offerte(u))
    identico = P.get("ricerca") == "identico"
    concorrente = P["modalita"] == "concorrente" and not identico
    valuta = confronta_identico if identico else confronta_param
    candidati, letti = {}, 0
    for q in query_ricerca(info, P):
        try:
            prodotti = cerca(q)
        except Exception:
            prodotti = []
        letti += len(prodotti)
        for l in prodotti:
            c = analizza(l["testo"])
            if not c.marca or not c.pollici or (c.marca != info.marca) != concorrente:
                continue
            ok, motivo, score = valuta(info, c, P)
            if ok and not identico and c.anno is None and P["anno"]["attivo"] and not P["anno"].get("accetta_ignoto", True):
                # tramite comparatore non c'è la pagina del negozio da verificare: senza anno certo non si propone
                c.anno = anno_da_idealo(br, c, paese, log) if not pr else None
                if c.anno != anno_obiettivo(P, info):
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": l["url"], "ricerca": dom,
                                             "esito": f"scartato: anno {c.anno or 'non determinabile'} (tramite {dom})"})
                    continue
                motivo = ", ".join(x for x in motivo.split(", ") if x and x != "anno da verificare") or "ok"
            if ok and l["url"] not in candidati:
                candidati[l["url"]] = (score, c, motivo)
        if len(candidati) >= 3:
            break
    if letti and not candidati:  # il comparatore risponde ma non ha nessun modello simile: non c'è nemmeno nel negozio
        out["dettaglio"].append({"retailer": r["nome"], "ricerca": dom,
                                 "esito": f"via {dom}: nessun modello simile tra {letti} prodotti"})
    scelti, codici = [], set()
    for url, (score, c, motivo) in sorted(candidati.items(), key=lambda x: x[1][0])[:5]:
        if len(scelti) >= max_m:
            break
        if c.codice in codici:
            continue
        try:
            offerte = offerte_di(url)
        except Exception:
            offerte = []
        # PriceRunner: il nome del negozio apre il testo dell'offerta ("Currys 4.5 ...", "AO ..."): deve iniziare così
        def del_negozio(o):
            n = re.sub(r"[^a-z0-9]", "", o["negozio"].lower())
            if not pr:
                return chiave in n
            # nomi corti (AO) devono aprire il testo; gli altri possono stare poco dopo (logo, "Valid until...")
            return n.startswith(chiave) or (len(chiave) >= 4 and chiave in n[:40])
        off = next((o for o in offerte if del_negozio(o)), None)
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
    """Ricava i dati dell'ASIN. La base è SEMPRE la pagina Amazon (titolo, scheda tecnica, prezzo), letta ora o
    nelle ultime settimane (archivio): così il risultato non cambia se il modello è scritto a mano oppure no.
    Il modello scritto a mano serve solo quando dalla pagina Amazon il codice non si ricava (o Amazon blocca).
    Ritorna dict: titolo, modello, img, fonte, nota, marca, prezzo, scheda (+ letto_amazon, modello_amazon)."""
    import datetime as _dt
    paese = (riga.get("paese") or "IT").upper()
    nome, manuale = riga.get("nome", ""), (riga.get("modello") or "").strip()
    noto = (anagrafica or {}).get(f"{riga['asin']}|{paese}") or (anagrafica or {}).get(riga["asin"]) or {}
    limite = (_dt.date.today() - _dt.timedelta(days=GIORNI_ARCHIVIO_AMAZON)).isoformat()
    if noto.get("letto_amazon") and noto.get("titolo") and noto.get("aggiornato", "") >= limite:
        # pagina Amazon già letta di recente: stessi dati, senza riaprirla
        a = {"titolo": noto["titolo"], "modello": noto.get("modello_amazon", ""), "img": noto.get("img", ""),
             "marca": noto.get("marca", ""), "prezzo": noto.get("prezzo", ""), "errore": ""}
        sch, fonte_base = dict(noto.get("scheda") or {}), "Amazon (letto il " + noto["aggiornato"] + ")"
    else:
        a = br.amazon(riga["asin"], AMAZON_DOMINIO.get(paese, "amazon.it"))
        sch, fonte_base = leggi_scheda(a.get("scheda")), "Amazon"
    letto = bool(a.get("titolo"))
    titolo = a.get("titolo") or nome or noto.get("titolo", "")
    mod_amz = a.get("modello") or sch.get("modello", "")
    marca = a.get("marca", "") or sch.get("marca", "") or riga.get("marca", "") or noto.get("marca", "")
    dati = {"titolo": titolo, "modello": mod_amz, "img": a.get("img", "") or noto.get("img", ""), "fonte": "", "nota": "",
            "marca": marca, "prezzo": a.get("prezzo", ""), "scheda": sch,
            "letto_amazon": letto, "modello_amazon": mod_amz}
    prezzo = leggi_prezzo(dati["prezzo"])
    info = arricchisci(analizza(titolo, mod_amz, marca, prezzo), sch)
    if letto and info.marca and info.pollici and info.codice:
        if manuale:
            log(f"   modello scritto a mano '{manuale}' non necessario: Amazon dice {info.codice}")
        return {**dati, "modello": mod_amz or info.codice, "fonte": fonte_base}
    if manuale:
        im = arricchisci(analizza(titolo, manuale, marca, prezzo), sch)
        if im.marca and im.pollici and (im.codice or (im.tecnologia and im.fascia)):
            return {**dati, "modello": manuale,
                    "fonte": (fonte_base + " + modello inserito") if letto else "inserito a mano",
                    "nota": "" if letto else (a.get("errore") or "pagina Amazon non leggibile") + ": usato il modello scritto a mano"}
    if letto and info.marca and info.pollici and info.tecnologia and info.fascia:
        # modello non in archivio (marca o serie nuova): si procede con i dati letti da Amazon
        nota = "modello non in archivio: dati ricavati dalla pagina Amazon"
        if info.fascia_fonte == "stimata":
            nota += f", fascia stimata dal prezzo ({dati['prezzo']})"
        return {**dati, "fonte": fonte_base, "nota": nota}
    # piano B: Amazon bloccato o pagina illeggibile -> motore di ricerca
    log(f"   Amazon non leggibile ({a.get('errore') or 'modello non trovato'}): provo la ricerca web")
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
    return {**dati, "nota": a.get("errore") or "modello Amazon non riconosciuto"}


def prepara_asin(br, riga, retailer, P, log=print, anagrafica=None):
    """Fase 1 (sequenziale, Amazon): riconosce l'ASIN. Ritorna (out, info); info è None se l'ASIN va saltato."""
    paese = (riga.get("paese") or "IT").upper()
    out = {"asin": riga["asin"], "paese": paese, "amazon": {}, "match": {}, "esito": {}, "dettaglio": [], "errore": ""}
    url_amz = f"https://www.{AMAZON_DOMINIO.get(paese, 'amazon.it')}/dp/{riga['asin']}"
    am = riconosci_amazon(br, riga, anagrafica, log)
    nome, modello, fonte, nota = am["titolo"], am["modello"], am["fonte"], am["nota"]
    info = arricchisci(analizza(nome, modello, am.get("marca", ""), leggi_prezzo(am.get("prezzo", ""))), am.get("scheda") or {})
    out["amazon"] = {"titolo": nome, "modello": info.codice or modello, "img": am["img"], "url": url_amz,
                     "fonte": fonte, "nota": nota, "marca_amazon": am.get("marca", ""), "prezzo": am.get("prezzo", ""),
                     "fascia_fonte": info.fascia_fonte, "marca_nuova": info.marca_nuova, "regola": info.regola,
                     "scheda": {k: v for k, v in (am.get("scheda") or {}).items() if k in ("anno", "pollici", "risoluzione", "tecnologia", "hz", "modello")},
                     "scheda_completa": am.get("scheda") or {}, "letto_amazon": am.get("letto_amazon", False),
                     "modello_amazon": am.get("modello_amazon", ""),
                     **info_dict(info)}
    log(f"   Amazon ({fonte or 'non riconosciuto'}): {info.marca} {info.codice} {info.pollici}\" {info.famiglia}")
    # per cercare un concorrente servono tecnologia e fascia dell'ASIN, altrimenti il confronto è casuale
    identico = P.get("ricerca") == "identico"
    non_classificato = P["modalita"] == "concorrente" and not identico and not (info.tecnologia and info.fascia)
    if identico and info.marca and info.pollici and (not info.codice or "caratteristiche" in info.note):
        out["errore"] = "codice modello non ricavabile da Amazon: per cercare lo stesso modello scrivilo a mano"
        out["esito"] = {r["nome"]: "saltato" for r in retailer}
        log("   ⚠ stesso modello: codice Amazon mancante")
        return out, None
    if e_accessorio(nome):
        out["errore"] = "non sembra una TV (accessorio o ricambio): controlla l'ASIN"
        out["esito"] = {r["nome"]: "saltato" for r in retailer}
        log("   ⚠ l'ASIN non sembra una TV")
        return out, None
    if not info.marca or not info.pollici or non_classificato:
        out["errore"] = nota or ("fascia del modello Amazon non riconosciuta" if non_classificato else "modello Amazon non riconosciuto")
        out["esito"] = {r["nome"]: "saltato" for r in retailer}
        log("   ⚠ modello Amazon non riconosciuto: scrivere il modello a mano")
        return out, None
    out["ponte"] = {}
    return out, info


def confronta_retailer(br, info, r, P, paese, log=print, stop=lambda: False):
    """Fase 2 (un negozio): cerca i modelli simili all'ASIN su un retailer.
    Ritorna {match, esito, dettaglio, ponte} per quel retailer (indipendente dagli altri: si può parallelizzare)."""
    identico = P.get("ricerca") == "identico"
    concorrente = P["modalita"] == "concorrente" and not identico
    valuta = confronta_identico if identico else confronta_param
    max_m = max(1, int(P.get("max_match") or 1))
    out = {"match": {}, "esito": {}, "dettaglio": [], "ponte": {}}
    r = {**r, "url": URL_CORRETTI.get(r["url"], r["url"])}
    validi, da_leggere = {}, {}
    pertinenti, ricerche_ok, errori, tv_letti = 0, 0, [], 0
    for q in query_ricerca(info, P):
        url_s, links, stato = br.cerca(r["url"], q)
        # 404 su una pagina di ricerca = nessun risultato, non un errore
        if stato == "ok" or stato == "HTTP 404":
            ricerche_ok += 1
        else:
            errori.append(stato)
            out["dettaglio"].append({"retailer": r["nome"], "esito": f"ricerca: {stato}", "url": url_s, "ricerca": q})
            if stato.startswith(("HTTP 403", "HTTP 429")) and not ricerche_ok:
                break  # sito che blocca: le altre ricerche darebbero lo stesso errore (si passa subito al ponte)
        for l in links:
            if l["url"].split("?")[0] == url_s.split("?")[0]:
                continue  # filtri della pagina di ricerca (marca, prezzo...), non prodotti
            if e_accessorio(l["testo"], l["url"]):
                continue  # telecomandi, staffe, cornici, elettrodomestici: non sono TV
            c = analizza(l["testo"], prezzo=leggi_prezzo(l["testo"]))
            if not c.codice or "caratteristiche" in c.note:
                # molti retailer mettono il codice modello solo nell'indirizzo (es. _tcl-75t69c-..., pidSAMQE75QN70H)
                # Unieuro: pid + 3 lettere della marca (pidSAMQE75QN70H, pidXIA50APRO2)
                slug = l["url"].split("?")[0].rsplit("/", 1)[-1]
                slug = re.sub(r"pid([A-Z]{3})", lambda m: f" {PID_MARCHE.get(m.group(1), '')} " + ("XIA" if m.group(1) == "XIA" else ""), slug)
                c2 = analizza(f"{l['testo']} {re.sub(r'[-_.]+', ' ', slug)}", prezzo=leggi_prezzo(l["testo"]))
                if c2.codice and "caratteristiche" not in c2.note and (not c.marca or c2.marca == c.marca) and \
                        (not c.pollici or c2.pollici == c.pollici):
                    c = c2
            if not c.marca or not c.pollici:
                continue
            tv_letti += 1
            if (c.marca != info.marca) == concorrente:
                if c.pollici == info.pollici:
                    pertinenti += 1
            else:
                continue  # stessa marca in modalità concorrente, o altra marca in modalità stessa marca
            ok, motivo, score = valuta(info, c, P)
            if not ok and motivo.startswith("codice modello non leggibile") and P.get("verifica_url", True) and \
                    abs(c.pollici - info.pollici) <= int(P["pollici"].get("tolleranza") or 0) and l["url"] not in da_leggere:
                da_leggere[l["url"]] = l  # titolo senza modello: si legge la scheda dell'inserzione (dopo, se serve)
            out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "famiglia": c.famiglia,
                                     "pollici": c.pollici, "anno": c.anno, "url": l["url"],
                                     "esito": ("VALIDO " if ok else "scartato: ") + motivo, "ricerca": q})
            if ok and l["url"] not in validi:
                validi[l["url"]] = (score, c, l.get("img", ""), motivo)
        if len(validi) >= max_m + 1:  # una riserva: la verifica della pagina può scartarne
            break
    # inserzioni della diagonale giusta ma senza modello nel titolo (es. "Téléviseur QLED 4K noir"):
    # si apre la pagina e si usano titolo completo e scheda tecnica (modello, tecnologia, anno...)
    for url, l in list(da_leggere.items())[:4]:
        if len(validi) >= max_m + 1 or (stop and stop()):
            break
        res = br.verifica(url)
        if not res[0]:
            continue
        sch_raw = res[4] if len(res) > 4 else {}
        sp = leggi_scheda({k: v for k, v in sch_raw.items() if not k.startswith("_")})
        c = arricchisci(analizza(f"{res[1]} {l['testo']}", sp.get("modello", ""), sp.get("marca", ""),
                                 prezzo=leggi_prezzo(l["testo"])), sp)
        if sp.get("pollici"):
            c.pollici = sp["pollici"]
        if not c.marca or not c.pollici or (c.marca != info.marca) != concorrente:
            continue
        ok, motivo, score = valuta(info, c, P)
        out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "famiglia": c.famiglia,
                                 "pollici": c.pollici, "anno": c.anno, "url": url,
                                 "esito": ("VALIDO " if ok else "scartato: ") + motivo + " (modello letto nella scheda dell'inserzione)"})
        if ok:
            validi[url] = (score, c, l.get("img", ""), motivo + ", modello dalla scheda")
    scelti, codici = [], set()
    for url, (score, c, im, motivo) in sorted(validi.items(), key=lambda x: x[1][0]):
        nome_pag = ""
        if len(scelti) >= max_m:
            break
        if c.codice in codici:
            continue
        if P.get("verifica_url", True):
            res = br.verifica(url)
            vivo, titolo_pag, corpo, og = res[:4]
            sch_raw = res[4] if len(res) > 4 else {}
            sp = leggi_scheda({k: v for k, v in sch_raw.items() if not k.startswith("_")})
            if not vivo:
                stato_p = sch_raw.get("_stato")
                if stato_p in (404, 410):  # prodotto davvero non più in vendita
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url, "esito": "URL non attivo"})
                    continue
                # pagina bloccata dal sito (anti-bot) o lenta: il prodotto c'è, si usano i dati della ricerca
                out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                         "esito": f"pagina prodotto non apribile ({stato_p or 'timeout'}): uso i dati della ricerca"})
                titolo_pag, corpo, og = c.testo, "", ""
                motivo = ", ".join(x for x in [motivo if motivo != "ok" else "", "pagina non verificabile"] if x)
            cp = analizza(titolo_pag)
            n_voci = len([k for k in sch_raw if not k.startswith("_")])
            letti = ", ".join(f"{k} {v}" for k, v in sp.items() if k in ("anno", "pollici", "risoluzione", "tecnologia", "hz") and v)
            if vivo:
                out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                         "esito": f"scheda tecnica: {letti or 'nessun dato utile'} ({n_voci} voci)"})
            pol_pag = sp.get("pollici") or (cp.pollici if cp.codice else None)
            if pol_pag and P["pollici"]["attivo"] and abs(pol_pag - info.pollici) > int(P["pollici"].get("tolleranza") or 0):
                out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                         "esito": f"pagina prodotto non coerente ({pol_pag}\")"})
                continue
            if identico:
                # stesso modello: la pagina deve mostrare lo stesso codice (se ne mostra uno) e lo stesso anno
                cpag = analizza(f"{sp.get('modello', '')} {titolo_pag}")
                if cpag.codice and cpag.marca == info.marca and "caratteristiche" not in cpag.note \
                        and not stesso_modello_esatto(info, cpag):
                    out["dettaglio"].append({"retailer": r["nome"], "modello": cpag.codice, "url": url,
                                             "esito": f"scartato: la pagina mostra un altro modello ({cpag.codice})"})
                    continue
                anno_pag = cp.anno or sp.get("anno") or c.anno
                if anno_pag and info.anno and anno_pag != info.anno:  # stesso modello, anno diverso nel titolo: lo si dice
                    motivo = ", ".join(x for x in [motivo if motivo != "ok" else "", f"anno nel negozio {anno_pag}, su Amazon {info.anno}"] if x)
            else:
                # caratteristiche: scheda tecnica, poi titolo; il testo libero della pagina solo per le funzioni HDR/HDMI
                full = arricchisci(analizza(f"{titolo_pag} {corpo[:20000]}", c.codice), sp)
                mancanti = [n for k, n in (("dolby_vision", "Dolby Vision"), ("hdr10plus", "HDR10+"),
                                           ("hdmi21", "HDMI 2.1"))
                            if P[k]["attivo"] and getattr(info, k) and not getattr(full, k)]
                # anno e risoluzione: scheda tecnica, altrimenti SOLO il titolo del prodotto (il resto della pagina
                # contiene menu, banner, copyright ed etichette energetiche con altri anni e risoluzioni)
                ris_pag = sp.get("risoluzione") or cp.risoluzione
                if P["risoluzione"]["attivo"] and info.risoluzione and ris_pag and ris_pag != info.risoluzione and \
                        not (P["modalita"] == "concorrente" and {ris_pag, info.risoluzione} <= {"HD", "FHD"}):
                    mancanti.append(f"risoluzione {info.risoluzione} (pagina: {ris_pag})")
                hz_pag = sp.get("hz")
                if P["refresh"]["attivo"] and info.hz and hz_pag and hz_diverse(hz_pag, info.hz):
                    mancanti.append(f"frequenza {info.hz} Hz (pagina: {hz_pag} Hz)")
                # la voce "tecnologia" delle schede è spesso generica o sbagliata (un QLED è anche "LED", un LED a volte
                # "Mini LED"): si scarta solo se una è OLED e l'altra no, oppure se anche il titolo della pagina la contraddice
                tec_pag = sp.get("tecnologia")
                if tec_pag and cp.tecnologia and cp.tecnologia != tec_pag and "OLED" not in (tec_pag, cp.tecnologia):
                    tec_pag = cp.tecnologia
                if P["tecnologia"]["attivo"] and tec_pag and c.fascia_fonte != "catalogo" and info.tecnologia and \
                        tec_pag != info.tecnologia and not _tec_equivalenti(info.tecnologia, tec_pag, P["tecnologia"].get("equivalenze")) and \
                        ("OLED" in (tec_pag, info.tecnologia) or (cp.tecnologia and cp.tecnologia != info.tecnologia)):
                    mancanti.append(f"tecnologia {info.tecnologia} (pagina: {tec_pag})")
                if mancanti:
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": "scartato: " + ", ".join(mancanti)})
                    continue
                anno_pag = cp.anno or sp.get("anno") or c.anno  # l'anno scritto nel titolo è più affidabile della scheda
                # anno su idealo solo se serve davvero (Stretto: un anno sconosciuto escluderebbe il modello)
                if not anno_pag and P["anno"]["attivo"] and not P["anno"].get("accetta_ignoto", True) and c.codice:
                    anno_pag = anno_da_idealo(br, c, paese, log)
                    if anno_pag:
                        out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                                 "esito": f"anno {anno_pag} letto su {IDEALO.get(paese, 'idealo')}"})
                        motivo = ", ".join(x for x in motivo.split(", ") if x and x != "ok") + (", " if motivo not in ("", "ok") else "") + f"anno da {IDEALO.get(paese, 'idealo')}"
                if anno_pag and P["anno"]["attivo"] and anno_pag != anno_obiettivo(P, info):
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": f"scartato: anno {anno_pag} (da pagina)"})
                    continue
                if not anno_pag and P["anno"]["attivo"] and not P["anno"].get("accetta_ignoto", True):
                    out["dettaglio"].append({"retailer": r["nome"], "modello": c.codice, "url": url,
                                             "esito": "scartato: anno non indicato nemmeno nella scheda tecnica"})
                    continue
                if anno_pag:  # anno letto in scheda, nel titolo o su idealo: non è più "da verificare"
                    c.anno = anno_pag
                    motivo = ", ".join(x for x in motivo.split(", ") if x and x != "anno da verificare") or "ok"
            im = og or im
            nome_pag = titolo_pag.strip()
            # il codice sulla pagina prodotto è il più affidabile: se c'è, vince
            if cp.codice and cp.marca == c.marca and cp.pollici == c.pollici and \
                    (stesso_modello_esatto(info, cp) if identico else not stesso_modello(info, cp)):
                c.codice = cp.codice
            # codice letto altrove nella pagina (es. "vedi anche 40MQF7000Z") ma la scheda dice un'altra diagonale:
            # si mostra il modello della scheda, o marca + caratteristiche, non un codice sbagliato
            m_pol = re.match(r"\D{0,4}(\d{2,3})", c.codice or "")
            if sp.get("pollici") and m_pol and int(m_pol.group(1)) != sp["pollici"] and int(m_pol.group(1)) in (24, 32, 40, 42, 43, 48, 50, 55, 58, 60, 65, 70, 75, 77, 83, 85, 98, 100):
                c.codice = sp.get("modello") or f"{c.marca.title()} {sp['pollici']}\" {c.tecnologia}".strip()
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
        log(f"   {r['nome']}: sito non leggibile, provo tramite {COMPARATORE.get(paese, 'comparatore')}")
        via = ponte_idealo(br, info, r, P, paese, out, max_m, log)
        out["ponte"][r["nome"]] = COMPARATORE.get(paese, "")
        if via:
            scelti = via
            out["match"][r["nome"]] = scelti
            esito = "trovato"
        elif any(d.get("retailer") == r["nome"] and str(d.get("esito", "")).startswith(f"via {COMPARATORE.get(paese)}: nessun")
                 for d in out["dettaglio"]):
            # sito bloccato, ma il comparatore mostra che quel negozio non vende modelli simili (o che non ne esistono)
            esito = "non_presente"
    out["esito"][r["nome"]] = esito
    testo = ", ".join(s["modello"] + (f" (via {s['via']})" if s.get("via") else "") for s in scelti) or ESITI[esito]
    if esito == "errore" and errori:
        testo += f" ({errori[-1]})"
    log(f"   {r['nome']}: {testo}")
    return out


# negozi dello stesso gruppo con lo stesso catalogo (stessa pagina prodotto, cambia solo il dominio)
GEMELLI = [("MediaMarkt", "mediamarkt.de", "Saturn", "saturn.de")]


def gemelli_da_controllare(out, nomi):
    """Coppie (da, a) in cui un negozio gemello ha trovato modelli e l'altro no."""
    coppie = []
    for a, da, b, db in GEMELLI:
        for src, d_src, dst, d_dst in ((a, da, b, db), (b, db, a, da)):
            if src in nomi and dst in nomi and (out.get("match") or {}).get(src) and not out["match"].get(dst) \
                    and out.get("esito", {}).get(dst) not in (None, "saltato"):
                coppie.append((src, d_src, dst, d_dst))
    return coppie


def completa_gemelli(br, out, retailer, log=print):
    """MediaMarkt e Saturn hanno lo stesso catalogo: se uno trova un modello e l'altro no,
    si apre la stessa pagina prodotto sull'altro sito (o si cerca il codice) e, se c'è, si aggiunge."""
    nomi = {r["nome"]: r for r in retailer}
    for src, d_src, dst, d_dst in gemelli_da_controllare(out, nomi):
        nuovi = []
        for m in out["match"][src]:
            if m.get("via") or d_src not in (m.get("url") or ""):
                continue
            rif = analizza(f"{m.get('modello', '')} {m.get('titolo', '')}")
            cod = _cod_norm(m.get("modello", ""))

            def stesso(testo):
                c = analizza(testo)
                return bool(cod and len(cod) >= 5 and cod in _cod_norm(testo)) or \
                    (c.codice and c.pollici == rif.pollici and stesso_modello_esatto(rif, c))
            url2 = m["url"].replace(d_src, d_dst)
            res = br.verifica(url2)
            trovato = url2 if res[0] and stesso(res[1]) else None
            if not trovato and m.get("modello"):
                _, links, _st = br.cerca(nomi[dst]["url"], m["modello"])
                for l in links:
                    if d_dst in l["url"] and "/product/" in l["url"] and stesso(l["testo"]):
                        trovato = l["url"]
                        break
            out["dettaglio"].append({"retailer": dst, "modello": m.get("modello", ""), "url": trovato or url2,
                                     "esito": (f"VALIDO stesso prodotto di {src}" if trovato
                                               else f"scartato: prodotto di {src} non presente su {dst}")})
            if trovato:
                nota = ", ".join(x for x in [m.get("nota", ""), f"stesso prodotto di {src}"] if x)
                nuovi.append({**m, "url": trovato, "nota": nota})
        if nuovi:
            out["match"][dst] = nuovi
            out["esito"][dst] = "trovato"
            log(f"   {dst}: {', '.join(x['modello'] for x in nuovi)} (stesso prodotto di {src})")
    return out


def unisci_retailer(out, parte):
    out["match"].update(parte["match"])
    out["esito"].update(parte["esito"])
    out["dettaglio"].extend(parte["dettaglio"])
    out.setdefault("ponte", {}).update(parte["ponte"])
    return out


def elabora_asin(br, riga, retailer, parametri, log=print, stop=lambda: False, anagrafica=None):
    """Versione sequenziale (exe e test): Amazon, poi un retailer alla volta.
    riga: {asin, paese, nome?, modello?}; retailer: [{nome, url}] del paese della riga."""
    P = unisci_parametri(parametri)
    out, info = prepara_asin(br, riga, retailer, P, log, anagrafica)
    if info is None:
        return out
    for r in retailer:
        if stop():
            break
        unisci_retailer(out, confronta_retailer(br, info, r, P, out["paese"], log, stop))
    if not stop():
        completa_gemelli(br, out, retailer, log)
    return out
