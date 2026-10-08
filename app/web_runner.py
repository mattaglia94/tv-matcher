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
        if not forza and time.time() - self.ultimo < 20:
            return
        self.ultimo = time.time()
        contenuto = base64.b64encode(json.dumps(dati, ensure_ascii=False).encode()).decode()
        for _ in range(3):
            if self.sha is None:
                st, info = _req("GET", f"{API}/repos/{REPO}/contents/{self.percorso}?ref={BRANCH}")
                self.sha = info.get("sha") if st == 200 else None
            corpo = {"message": f"run {RUN_ID}: {dati['stato']}", "content": contenuto, "branch": BRANCH}
            if self.sha:
                corpo["sha"] = self.sha
            st, res = _req("PUT", f"{API}/repos/{REPO}/contents/{self.percorso}", corpo)
            if st in (200, 201):
                self.sha = res["content"]["sha"]
                return
            self.sha = None  # conflitto: rilegge lo sha e riprova
            time.sleep(2)
        print(f"⚠ salvataggio stato non riuscito ({st})")


def main():
    from browser import Browser
    from nucleo import elabora_asin

    cfg = json.loads(os.environ.get("CONFIG") or open(sys.argv[1], encoding="utf-8").read())
    asins = cfg.get("asin", [])
    retailer = [r for r in cfg.get("retailer", []) if r.get("attivo", True)]
    parametri = cfg.get("parametri", {})
    per_paese = {}
    for r in retailer:
        per_paese.setdefault(r["paese"].upper(), []).append(r)
    totale = sum(len(per_paese.get(a.get("paese", "IT").upper(), [])) for a in asins) or 1

    if REPO and TOKEN:
        assicura_branch()
    pub = Pubblicatore(f"runs/{RUN_ID}/stato.json")
    stato = {"id": RUN_ID, "nome": cfg.get("nome", ""), "stato": "in_corso",
             "github_run": os.environ.get("GITHUB_RUN_ID", ""),
             "iniziato": dt.datetime.utcnow().isoformat() + "Z", "finito": None,
             "config": {"asin": asins, "retailer": retailer, "parametri": parametri},
             "avanzamento": {"fatti": 0, "totale": totale, "corrente": "Avvio del browser"},
             "log": [], "risultati": []}

    def log(m):
        print(m, flush=True)
        stato["log"] = (stato["log"] + [f"{dt.datetime.utcnow():%H:%M:%S} {m}"])[-80:]
        pub.salva(stato)

    pub.salva(stato, forza=True)
    br = None
    try:
        br = Browser(visibile=False, log=log)
        for i, a in enumerate(asins, 1):
            paese = a.get("paese", "IT").upper()
            ret = per_paese.get(paese, [])
            stato["avanzamento"]["corrente"] = f"ASIN {i}/{len(asins)} · {a['asin']} ({paese})"
            log(f"[{i}/{len(asins)}] {a['asin']} · {paese}")

            def log_ret(m):
                if m.strip().split(":")[0] in {r["nome"] for r in ret}:
                    stato["avanzamento"]["fatti"] += 1
                log(m)
            res = elabora_asin(br, a, ret, parametri, log=log_ret)
            if res.get("errore") and not res["match"]:
                stato["avanzamento"]["fatti"] += len(ret)
            stato["risultati"].append(res)
            pub.salva(stato, forza=True)
        stato["stato"] = "completato"
    except Exception as e:
        stato["stato"] = "errore"
        stato["errore"] = f"{e}"
        print(traceback.format_exc())
    finally:
        if br:
            br.chiudi()
        stato["finito"] = dt.datetime.utcnow().isoformat() + "Z"
        stato["avanzamento"]["corrente"] = {"completato": "Completato", "errore": "Interrotto per errore"}.get(stato["stato"], "")
        pub.salva(stato, forza=True)
    if stato["stato"] == "errore":
        sys.exit(1)


if __name__ == "__main__":
    main()
