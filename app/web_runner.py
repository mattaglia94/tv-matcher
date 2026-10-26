"""Runner lanciato dal sito (workflow "Run dal sito").
Legge la configurazione dalla variabile CONFIG e salva avanzamento e risultati
nel branch `dati` del repository: runs/<RUN_ID>/stato.json.
Il sito legge quel file, quindi la sessione si riprende da qualsiasi dispositivo."""
import base64
import datetime as dt
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.environ.get("REPO", "")
TOKEN = os.environ.get("GH_TOKEN", "")
RUN_ID = os.environ.get("RUN_ID", "locale")
# ricerche grandi: divise in "parti" su più macchine GitHub in parallelo; ogni parte scrive runs/<id>/parte_<k>.json
PARTE, PARTI = int(os.environ.get("PARTE", "0")), max(1, int(os.environ.get("PARTI", "1")))
BRANCH = "dati"
API = "https://api.github.com"


def _req(metodo, url, corpo=None):
    data = json.dumps(corpo).encode() if corpo is not None else None
    r = urllib.request.Request(url, data=data, method=metodo, headers={
        "Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "tv-matcher"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def assicura_branch():
    st, _ = _req("GET", f"{API}/repos/{REPO}/git/ref/heads/{BRANCH}")
    if st == 200:
        return
    st, repo = _req("GET", f"{API}/repos/{REPO}")
    base = repo.get("default_branch", "main")
    st, ref = _req("GET", f"{API}/repos/{REPO}/git/ref/heads/{base}")
    _req("POST", f"{API}/repos/{REPO}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": ref["object"]["sha"]})


def aggiorna_json(percorso, modifica, tentativi=6):
    """Legge-modifica-scrive con controllo di versione: più parti possono aggiornare lo stesso file senza perdere dati."""
    for _ in range(tentativi):
        st, info = _req("GET", f"{API}/repos/{REPO}/contents/{percorso}?ref={BRANCH}")
        attuale, sha = None, None
        if st == 200:
            sha = info.get("sha")
            try:
                attuale = json.loads(base64.b64decode(info["content"]).decode()) if info.get("content") else None
            except Exception:
                attuale = None
            if attuale is None and info.get("download_url"):  # file > 1 MB: contenuto da scaricare a parte
                try:
                    r = urllib.request.Request(info["download_url"], headers={"Authorization": f"Bearer {TOKEN}"})
                    attuale = json.loads(urllib.request.urlopen(r, timeout=60).read())
                except Exception:
                    attuale = None
        nuovo = modifica(attuale)
        corpo = {"message": f"run {RUN_ID}: {percorso}", "branch": BRANCH,
                 "content": base64.b64encode(json.dumps(nuovo, ensure_ascii=False).encode()).decode()}
        if sha:
            corpo["sha"] = sha
        st, _ = _req("PUT", f"{API}/repos/{REPO}/contents/{percorso}", corpo)
        if st in (200, 201):
            return True
        time.sleep(2 + PARTE)
    print(f"⚠ {percorso} non aggiornato")
    return False


def leggi_json(percorso):
    if not REPO or not TOKEN:
        return None
    st, info = _req("GET", f"{API}/repos/{REPO}/contents/{percorso}?ref={BRANCH}")
    if st != 200:
        return None
    try:
        if info.get("content"):
            return json.loads(base64.b64decode(info["content"]).decode())
        r = urllib.request.Request(info["download_url"], headers={"Authorization": f"Bearer {TOKEN}"})  # file > 1 MB
        return json.loads(urllib.request.urlopen(r, timeout=60).read())
    except Exception:
        return None


class Pubblicatore:
    def __init__(self, percorso):
        self.percorso = percorso
        self.sha = None
        self.ultimo = 0

    def salva(self, dati, forza=False):
        if not REPO or not TOKEN:  # esecuzione locale: scrive su file
            os.makedirs("output", exist_ok=True)
            with open(os.path.join("output", "stato.json"), "w", encoding="utf-8") as f:
                json.dump(dati, f, ensure_ascii=False, indent=1)
            return
        # GITHUB_TOKEN: max ~1.000 richieste l'ora per repository, da dividere tra le parti in parallelo
        if not forza and time.time() - self.ultimo < (20 if PARTI == 1 else 45):
            return
        self.ultimo = time.time()
        contenuto = base64.b64encode(json.dumps(dati, ensure_ascii=False).encode()).decode()
        for _ in range(3):
            if self.sha is None:
                st, info = _req("GET", f"{API}/repos/{REPO}/contents/{self.percorso}?ref={BRANCH}")
                self.sha = info.get("sha") if st == 200 else None
            corpo = {"message": f"run {RUN_ID}: {dati.get('stato', 'anagrafica') if isinstance(dati, dict) else ''}", "content": contenuto, "branch": BRANCH}
            if self.sha:
                corpo["sha"] = self.sha
            st, res = _req("PUT", f"{API}/repos/{REPO}/contents/{self.percorso}", corpo)
            if st in (200, 201):
                self.sha = res["content"]["sha"]
                if self.percorso.endswith(f"parte_{PARTE}.json"):
                    scrivi_unito(forza=isinstance(dati, dict) and dati.get("stato") != "in_corso")
                return
            self.sha = None  # conflitto: rilegge lo sha e riprova
            time.sleep(2)
        print(f"⚠ salvataggio stato non riuscito ({st})")


def unisci_parti(parti):
    """Stato unico da più parti (stessa logica del sito, web/api/stato.js)."""
    parti = sorted([p for p in parti if p], key=lambda p: p.get("parte", 0))
    if not parti:
        return None
    attesi = parti[0].get("parti", len(parti))
    stati = [p.get("stato") for p in parti]
    in_corso = "in_corso" in stati or len(parti) < attesi
    fatti = sum((p.get("avanzamento") or {}).get("fatti", 0) for p in parti)
    totale = sum((p.get("avanzamento") or {}).get("totale", 0) for p in parti)
    log = sorted(r.replace(" ", f" [{k + 1}] ", 1) for k, p in enumerate(parti) for r in p.get("log", []))[-120:]
    return {**parti[0], "stato": "in_corso" if in_corso else "errore" if "errore" in stati else "completato",
            "errore": " · ".join(p["errore"] for p in parti if p.get("errore")) or None,
            "iniziato": min(p.get("iniziato") or "9" for p in parti),
            "finito": None if in_corso else max(p.get("finito") or "" for p in parti),
            "avanzamento": {"fatti": fatti, "totale": max(totale, fatti, 1),
                            "corrente": f"{attesi} parti in parallelo" if in_corso else "Completato"},
            "log": log, "risultati": sorted((r for p in parti for r in p.get("risultati", [])), key=lambda r: r.get("_i", 0))}


_ultimo_unito = [0.0]


def scrivi_unito(forza=False):
    """Con più parti si aggiorna anche runs/<id>/stato.json con la vista complessiva."""
    # durante la ricerca lo aggiorna solo la parte 0 (ogni 3 minuti); alla fine ogni parte lo riscrive una volta
    if PARTI == 1 or not REPO or not TOKEN or (not forza and (PARTE != 0 or time.time() - _ultimo_unito[0] < 180)):
        return
    _ultimo_unito[0] = time.time()
    st, elenco = _req("GET", f"{API}/repos/{REPO}/contents/runs/{RUN_ID}?ref={BRANCH}")
    nomi = [f["name"] for f in elenco] if st == 200 and isinstance(elenco, list) else []
    parti = [leggi_json(f"runs/{RUN_ID}/{n}") for n in nomi if n.startswith("parte_")]
    unito = unisci_parti(parti)
    if unito:
        def piu_recente(vecchio):  # mai sostituire una vista più avanti (un'altra parte ha appena scritto dopo)
            v = (vecchio or {}).get("avanzamento", {}).get("fatti", -1)
            if vecchio and (vecchio.get("stato") != "in_corso" and unito["stato"] == "in_corso" or v > unito["avanzamento"]["fatti"]):
                return vecchio
            return unito
        aggiorna_json(f"runs/{RUN_ID}/stato.json", piu_recente)


MAX_PROCESSI = int(os.environ.get("MAX_PROCESSI", "8"))  # browser in parallelo in tutto
PER_NEGOZIO = int(os.environ.get("PER_NEGOZIO", "2"))     # browser contemporanei sullo stesso negozio


def lavoratore(retailer_gruppo, P, catalogo, cache, coda_in, coda_out):
    """Processo per uno o più negozi: ha un browser suo e confronta gli ASIN man mano che arrivano.
    Negozi diversi lavorano in parallelo; sullo stesso negozio le richieste restano una alla volta."""
    import traceback as tb
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from browser import Browser
    from nucleo import confronta_retailer
    from regole import imposta_catalogo
    imposta_catalogo(catalogo)
    log = lambda m: coda_out.put(("log", m))  # noqa: E731
    br = None
    try:
        br = Browser(visibile=False, log=log, cache=cache)
        while True:
            job = coda_in.get()
            if job is None:
                break
            idx, info, paese, nome_r = job
            r = retailer_gruppo[nome_r]
            try:
                parte = confronta_retailer(br, info, r, P, paese, log)
            except Exception as e:  # un errore su un negozio non ferma gli altri
                log(f"   {nome_r}: errore ({e})")
                print(tb.format_exc(), flush=True)
                parte = {"match": {nome_r: []}, "esito": {nome_r: "errore"}, "ponte": {},
                         "dettaglio": [{"retailer": nome_r, "esito": f"errore del motore: {e}"}]}
            coda_out.put(("ris", idx, nome_r, parte))
    finally:
        nuova = br.cache_nuova() if br else {}
        if br:
            br.chiudi()
        coda_out.put(("fine", list(retailer_gruppo), nuova))


def main():
    import multiprocessing as mp
    import queue as q_mod
    from browser import Browser
    from nucleo import prepara_asin, unisci_retailer
    from regole import catalogo_predefinito, imposta_catalogo, unisci_catalogo, unisci_parametri

    cfg = json.loads(os.environ.get("CONFIG") or open(sys.argv[1], encoding="utf-8").read())
    tutti = cfg.get("asin", [])
    asins = [dict(a, _i=i) for i, a in enumerate(tutti) if i % PARTI == PARTE]
    retailer = [r for r in cfg.get("retailer", []) if r.get("attivo", True)]
    parametri = cfg.get("parametri", {})
    P = unisci_parametri(parametri)
    per_paese = {}
    for r in retailer:
        per_paese.setdefault(r["paese"].upper(), []).append(r)
    totale = sum(len(per_paese.get(a.get("paese", "IT").upper(), [])) for a in asins) or 1

    if REPO and TOKEN:
        assicura_branch()
    pub = Pubblicatore(f"runs/{RUN_ID}/stato.json" if PARTI == 1 else f"runs/{RUN_ID}/parte_{PARTE}.json")
    anagrafica = leggi_json("config/anagrafica_asin.json") or {}
    # catalogo marche e serie: predefinito + modifiche fatte dal sito
    catalogo = unisci_catalogo(catalogo_predefinito(), leggi_json("config/catalogo.json"))
    imposta_catalogo(catalogo)
    cache = pulisci_cache(leggi_json("cache/pagine.json") or {})
    anagrafica_nuova = {}
    stato = {"id": RUN_ID, "nome": cfg.get("nome", ""), "stato": "in_corso",
             "github_run": os.environ.get("GITHUB_RUN_ID", ""),
             "iniziato": dt.datetime.utcnow().isoformat() + "Z", "finito": None,
             "config": {"asin": tutti, "retailer": retailer, "parametri": parametri},
             "parte": PARTE, "parti": PARTI,
             "avanzamento": {"fatti": 0, "totale": totale, "corrente": "Avvio del browser"},
             "log": [], "risultati": []}

    def log(m):
        print(m, flush=True)
        stato["log"] = (stato["log"] + [f"{dt.datetime.utcnow():%H:%M:%S} {m}"])[-80:]
        pub.salva(stato)

    pub.salva(stato, forza=True)
    br = None
    ctx = mp.get_context("spawn")
    coda_out = ctx.Queue()
    processi, code_in, gruppo_di = [], [], {}
    attesi = 0
    cache_nuova = {}

    def raccogli(blocca=False):
        nonlocal attesi
        while True:
            try:
                ev = coda_out.get(timeout=2 if blocca else 0.05)
            except q_mod.Empty:
                return
            if ev[0] == "log":
                log(ev[1])
            elif ev[0] == "ris":
                _, idx, nome_r, parte = ev
                unisci_retailer(stato["risultati"][idx], parte)
                stato["avanzamento"]["fatti"] += 1
                attesi -= 1
                pub.salva(stato)
            elif ev[0] == "fine":
                cache_nuova.update(ev[2])
            if blocca and attesi <= 0:
                return

    try:
        # negozi divisi in gruppi: ogni gruppo ha un processo con il suo browser
        # fino a PER_NEGOZIO browser per negozio (carico cortese per il sito), al massimo MAX_PROCESSI in tutto;
        # gli ASIN di un negozio si alternano tra i suoi browser
        nomi = [r["nome"] for r in retailer]
        slot = [r for k in range(PER_NEGOZIO) for r in retailer][:max(MAX_PROCESSI, len(nomi))]
        n_proc = max(1, min(MAX_PROCESSI, len(slot)))
        gruppi = [dict() for _ in range(n_proc)]
        for j, r in enumerate(slot):
            k = j % n_proc
            gruppi[k][r["nome"]] = r
            if k not in gruppo_di.setdefault(r["nome"], []):
                gruppo_di[r["nome"]].append(k)
        for k, gruppo in enumerate(gruppi):
            qi = ctx.Queue()
            pr = ctx.Process(target=lavoratore, args=(gruppo, P, catalogo, cache, qi, coda_out), daemon=True)
            pr.start()
            processi.append(pr)
            code_in.append(qi)
        giro = {n: 0 for n in gruppo_di}
        log(f"Motore avviato: {len(nomi)} negozi su {n_proc} browser in parallelo")
        br = Browser(visibile=False, log=log, cache=cache)  # Amazon: un ASIN alla volta
        for i, a in enumerate(asins, 1):
            paese = a.get("paese", "IT").upper()
            ret = per_paese.get(paese, [])
            stato["avanzamento"]["corrente"] = f"ASIN {i}/{len(asins)} · {a['asin']} ({paese})"
            log(f"[{i}/{len(asins)}] {a['asin']} · {paese}")
            out, info = prepara_asin(br, a, ret, P, log, anagrafica)
            out["_i"] = a["_i"]  # posizione nella lista originale (per riunire le parti)
            stato["risultati"].append(out)
            idx = len(stato["risultati"]) - 1
            am = out.get("amazon", {})
            if am.get("letto_amazon") and not am.get("fonte", "").startswith("Amazon (letto"):
                # pagina Amazon appena letta: in archivio i dati grezzi, riusati per 20 giorni (con o senza modello a mano)
                anagrafica_nuova[f"{a['asin']}|{paese}"] = {
                    "titolo": am.get("titolo", ""), "img": am.get("img", ""), "marca": am.get("marca_amazon", ""),
                    "prezzo": am.get("prezzo", ""), "scheda": am.get("scheda_completa") or {},
                    "modello_amazon": am.get("modello_amazon", ""), "modello": am.get("modello", ""),
                    "letto_amazon": True, "fonte": am["fonte"], "aggiornato": dt.date.today().isoformat()}
            if info is None:
                stato["avanzamento"]["fatti"] += len(ret)
            else:
                for r in ret:
                    ks = gruppo_di[r["nome"]]
                    code_in[ks[giro[r["nome"]] % len(ks)]].put((idx, info, paese, r["nome"]))
                    giro[r["nome"]] += 1
                    attesi += 1
            pub.salva(stato, forza=True)
            raccogli()
        br.chiudi()
        br = None
        stato["avanzamento"]["corrente"] = "Confronto sui negozi in corso"
        for qi in code_in:
            qi.put(None)
        while attesi > 0 and any(p.is_alive() for p in processi):
            raccogli(blocca=True)
        raccogli()
        if attesi > 0:
            raise RuntimeError(f"{attesi} confronti non completati (un browser si è chiuso)")
        # MediaMarkt e Saturn (stesso gruppo, stesso catalogo): se uno ha trovato il modello e l'altro no, si ricontrolla
        from nucleo import completa_gemelli, gemelli_da_controllare
        da_fare = [o for o in stato["risultati"]
                   if gemelli_da_controllare(o, {r["nome"] for r in per_paese.get(o.get("paese", ""), [])})]
        if da_fare:
            stato["avanzamento"]["corrente"] = "Controllo MediaMarkt / Saturn"
            log(f"Controllo incrociato MediaMarkt / Saturn su {len(da_fare)} ASIN")
            br = Browser(visibile=False, log=log, cache=cache)
            for o in da_fare:
                try:
                    completa_gemelli(br, o, per_paese.get(o["paese"], []), log)
                except Exception as e:  # il controllo in più non deve far fallire la ricerca
                    log(f"   controllo MediaMarkt / Saturn non riuscito ({e})")
                pub.salva(stato)
            cache_nuova.update(br.cache_nuova())
            br.chiudi()
            br = None
        stato["stato"] = "completato"
    except Exception as e:
        stato["stato"] = "errore"
        stato["errore"] = f"{e}"
        print(traceback.format_exc())
    finally:
        if br:
            br.chiudi()
        for p in processi:
            p.join(timeout=20)
        raccogli()
        stato["finito"] = dt.datetime.utcnow().isoformat() + "Z"
        stato["avanzamento"]["corrente"] = {"completato": "Completato", "errore": "Interrotto per errore"}.get(stato["stato"], "")
        pub.salva(stato, forza=True)
        if anagrafica_nuova and REPO and TOKEN:
            aggiorna_json("config/anagrafica_asin.json", lambda ana: {**(ana or {}), **anagrafica_nuova})
            print(f"Anagrafica ASIN aggiornata: {len(anagrafica_nuova)} modelli")
        if cache_nuova and REPO and TOKEN:
            aggiorna_json("cache/pagine.json", lambda c: pulisci_cache({**(c or {}), **cache_nuova}))
            print(f"Cache pagine aggiornata: {len(cache_nuova)} nuove")
    if stato["stato"] == "errore":
        sys.exit(1)


def pulisci_cache(c, giorni=30, massimo=4000):
    """Tiene solo le voci recenti (pagine prodotto e anni letti negli ultimi 30 giorni)."""
    limite = (dt.datetime.utcnow() - dt.timedelta(days=giorni)).strftime("%Y-%m-%d")
    voci = [(k, v) for k, v in c.items() if isinstance(v, dict) and v.get("data", "") >= limite]
    voci.sort(key=lambda kv: kv[1].get("data", ""), reverse=True)
    return dict(voci[:massimo])


if __name__ == "__main__":
    main()
