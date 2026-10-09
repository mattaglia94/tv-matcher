"""Navigazione con browser reale (Edge/Chrome già installato) tramite Playwright.
Legge Amazon (titolo + numero modello) e le pagine di ricerca dei retailer.
L'estrazione dei prodotti è generica: prende tutti i link della pagina e tiene
quelli il cui testo sembra un TV della marca/pollici cercati. Così non dipende
dal layout specifico di ogni sito."""
import random
import re
import time
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

COOKIE_TESTI = ["Accetta tutti", "Accetta", "Accetto", "Accept all", "Accept All", "Accept",
                "Alle akzeptieren", "Akzeptieren", "Tout accepter", "Accepter",
                "Aceptar todo", "Aceptar", "Ok", "OK", "Consenti tutti", "Agree"]

MODELLO_ETICHETTE = ["Numero modello articolo", "Numero modello", "Modellnummer",
                     "Model number", "Item model number", "Numéro du modèle",
                     "Référence du modèle", "Número de modelo", "Modello"]

JS_LINKS = """
() => {
  const out = [];
  document.querySelectorAll('a[href]').forEach(a => {
    let t = (a.innerText || '') + ' ' + (a.getAttribute('title') || '') + ' ' + (a.getAttribute('aria-label') || '');
    const img = a.querySelector('img[alt]'); if (img) t += ' ' + img.alt;
    // testo del riquadro prodotto (titolo spesso in un nodo vicino)
    const card = a.closest('article, li, [class*="product" i], [class*="tile" i], [data-test*="product" i]');
    if (card && card.innerText && card.innerText.length < 600) t += ' ' + card.innerText;
    t = t.replace(/\\s+/g, ' ').trim();
    let im = a.querySelector('img') || (card && card.querySelector('img'));
    let src = '';
    if (im) src = im.currentSrc || im.src || im.getAttribute('data-src') || im.getAttribute('data-lazy') || '';
    if (src.startsWith('data:')) src = im.getAttribute('data-src') || '';
    if (t.length > 12) out.push({href: a.href, testo: t.slice(0, 600), img: src});
  });
  return out;
}
"""


JS_SCHEDA = r"""
() => {
  // scheda tecnica dell'inserzione: coppie voce -> valore (tabelle, elenchi, dati strutturati per Google)
  const out = {};
  const pulisci = (t) => (t || '').replace(/[\u200e\u200f]/g, '').replace(/\s+/g, ' ').trim();
  const add = (k, v) => {
    k = pulisci(k).replace(/[\s:]+$/, ''); v = pulisci(v);
    if (!k || !v || k.length > 70 || v.length > 200 || k === v) return;
    const kl = k.toLowerCase();
    if (!(kl in out) && Object.keys(out).length < 400) out[kl] = v;
  };
  document.querySelectorAll('tr').forEach((tr) => { const c = tr.querySelectorAll('th, td'); if (c.length === 2) add(c[0].innerText, c[1].innerText); });
  document.querySelectorAll('dl').forEach((dl) => { const dt = dl.querySelectorAll('dt'), dd = dl.querySelectorAll('dd'); dt.forEach((d, i) => dd[i] && add(d.innerText, dd[i].innerText)); });
  document.querySelectorAll('li, [class*="spec" i] > div, [class*="feature" i] > div, [class*="attribute" i] > div').forEach((el) => {
    const t = pulisci(el.innerText);
    const m = t.match(/^([^:]{2,60}?)\s*:\s*(.{1,150})$/);
    if (m && el.children.length < 6) add(m[1], m[2]);
  });
  document.querySelectorAll('script[type="application/ld+json"]').forEach((sc) => {
    try {
      const j = JSON.parse(sc.textContent);
      (Array.isArray(j) ? j : (j['@graph'] || [j])).forEach((q) => {
        if (!q || !/Product/i.test(String(q['@type']))) return;
        if (q.name) add('ld:nome', q.name);
        if (q.model) add('ld:modello', typeof q.model === 'string' ? q.model : q.model.name);
        if (q.mpn) add('ld:mpn', q.mpn);
        if (q.brand) add('ld:marca', q.brand.name || q.brand);
        if (q.releaseDate) add('ld:data', q.releaseDate);
        (q.additionalProperty || []).forEach((a) => add(a.name, String(a.value)));
        const o = Array.isArray(q.offers) ? q.offers[0] : q.offers;
        if (o && o.price) add('ld:prezzo', o.price + ' ' + (o.priceCurrency || ''));
      });
    } catch (e) { /* JSON non valido */ }
  });
  return out;
}
"""


class _RispostaFinta:
    def __init__(self, status):
        self.status = status


JS_OFFERTE = """
() => [...document.querySelectorAll('#offerList li, li[class*=productOffers-listItem]')].map(li => {
  const a = li.querySelector('a[href*="relocator"], a[href*="/go/"], a[href*="redirect"]') || li.querySelector('a[href]');
  const alts = [...li.querySelectorAll('img')].map(i => i.alt || '').join(' / ');
  const prezzo = (li.innerText.match(/(?:€|£)\\s?[\\d.,]+|[\\d.,]+\\s?(?:€|£)/) || [''])[0];
  const img = [...li.querySelectorAll('img')].map(i => i.currentSrc || i.src || '').find(s => s && !s.startsWith('data:')) || '';
  return {url: a ? a.href : '', negozio: alts + ' ' + (li.getAttribute('data-shop-name') || ''),
          testo: (li.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 400), prezzo, img};
}).filter(o => o.url && o.testo.length > 20)
"""


class Browser:
    def __init__(self, visibile=False, log=print, cache=None, leggero=True):
        self.log = log
        self._cache = cache if cache is not None else {}   # pagine prodotto lette di recente (persistente, 30 giorni)
        self._nuova = {}                                     # voci aggiunte in questa esecuzione
        self._ricerche = {}                                  # ricerche già fatte in questa esecuzione
        self.pw = sync_playwright().start()
        self.b = None
        for canale in ("msedge", "chrome", None):
            try:
                self.b = self.pw.chromium.launch(channel=canale, headless=not visibile,
                                                 args=["--disable-blink-features=AutomationControlled"])
                self.log(f"Browser avviato: {canale or 'chromium'}")
                break
            except Exception:
                continue
        if not self.b:
            raise RuntimeError("Nessun browser trovato: installa Microsoft Edge o Google Chrome.")
        self.ctx = self.b.new_context(
            locale="it-IT", viewport={"width": 1400, "height": 1000},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 Edg/130.0"))
        if leggero:  # niente immagini, video e font: le pagine si caricano molto prima (le foto restano come link)
            self.ctx.route("**/*", lambda route: route.abort() if route.request.resource_type in ("image", "media", "font")
                           else route.continue_())
        self.page = self.ctx.new_page()
        self._cookie_ok = set()
        self._riscaldati = set()   # domini già visitati dalla home (cookie anti-bot ottenuti)
        self._idealo_azione = {}   # dominio idealo -> URL del modulo di ricerca

    def cache_get(self, k):
        return self._cache.get(k)

    def cache_put(self, k, v):
        v = {**v, "data": time.strftime("%Y-%m-%d")}
        self._cache[k] = v
        self._nuova[k] = v

    def cache_nuova(self):
        return dict(self._nuova)

    def chiudi(self):
        try:
            self.b.close()
            self.pw.stop()
        except Exception:
            pass

    def _pausa(self, a=0.8, b=1.8):
        time.sleep(random.uniform(a, b))

    def _cookie(self, dominio):
        if dominio in self._cookie_ok:
            return
        for testo in COOKIE_TESTI:
            try:
                btn = self.page.get_by_role("button", name=testo, exact=True)
                if btn.count():
                    btn.first.click(timeout=2000)
                    self._cookie_ok.add(dominio)
                    time.sleep(1)
                    return
            except Exception:
                continue
        try:  # OneTrust, il più diffuso
            self.page.click("#onetrust-accept-btn-handler", timeout=1500)
            self._cookie_ok.add(dominio)
        except Exception:
            pass

    def _vai(self, url):
        try:
            r = self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except PWTimeout:
            return None
        except Exception as e:  # navigazione interrotta (ERR_ABORTED, redirect via script...): riprovo una volta
            if "ERR_ABORTED" not in str(e) and "interrupted" not in str(e):
                return None
            try:
                time.sleep(1)
                r = self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception:
                return None
        try:  # i siti di e-commerce non sono quasi mai "fermi": breve attesa, non fino al limite
            self.page.wait_for_load_state("networkidle", timeout=2500)
        except PWTimeout:
            pass
        r = self._attendi_verifica(r)
        dominio = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        self._cookie(dominio)
        for _ in range(3):  # scroll per caricare i prodotti "lazy"
            self.page.mouse.wheel(0, 3000)
            time.sleep(0.35)
        return r

    def _in_verifica(self):
        try:
            t = self.page.title().lower()
        except Exception:
            return False
        return any(x in t for x in ("ci siamo quasi", "just a moment", "un momento", "attention required",
                                    "verifica di sicurezza", "einen moment", "un instant"))

    def _attendi_verifica(self, r):
        """Pagine di verifica anti-bot non interattive (es. Cloudflare): spesso si superano da sole in pochi secondi."""
        if not self._in_verifica():
            return r
        for _ in range(10):
            time.sleep(3)
            if not self._in_verifica():
                try:
                    self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                except PWTimeout:
                    pass
                return _RispostaFinta(200)
        return r

    def riscalda(self, url):
        """Prima ricerca su un dominio: passa dalla home, così il sito rilascia i cookie di sessione/anti-bot."""
        m = re.match(r"(https?://[^/]+)", url)
        if not m or m.group(1) in self._riscaldati:
            return
        self._riscaldati.add(m.group(1))
        self._vai(m.group(1) + "/")
        self._pausa(1.5, 3)

    # ------------------------------------------------------------ Amazon
    def _amazon_continua(self):
        """Pagina intermedia "Fai clic sul pulsante qui sotto per continuare a fare acquisti": basta un clic."""
        try:
            corpo = self.page.inner_text("body", timeout=3000)[:400].lower()
        except Exception:
            return False
        if not any(x in corpo for x in ("continua con gli acquisti", "continue shopping", "weiter einkaufen",
                                        "continuer les achats", "seguir comprando")):
            return False
        try:
            self.page.locator("button, input[type=submit], a.a-button-text").first.click(timeout=4000)
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            time.sleep(random.uniform(1.5, 3))
            return True
        except Exception:
            return False

    def _amazon_bloccato(self):
        html = self.page.content().lower()
        return ("validatecaptcha" in html or "captcha" in html or "robot check" in html) \
            and "producttitle" not in html and 'id="title"' not in html

    def amazon(self, asin, dominio):
        """Legge titolo, numero modello e foto. Prova più indirizzi prima di arrendersi al captcha."""
        if dominio not in self._cookie_ok:  # prima visita: home page per ottenere i cookie di sessione
            self._vai(f"https://www.{dominio}/")
            self._cookie_ok.add(dominio)
            self._pausa(2, 4)
        tentativi = [f"https://www.{dominio}/dp/{asin}",
                     f"https://www.{dominio}/gp/product/{asin}?psc=1",
                     f"https://www.{dominio}/gp/aw/d/{asin}"]  # versione mobile
        url = tentativi[0]
        for i, u in enumerate(tentativi):
            self._vai(u)
            self._pausa()
            if self._amazon_continua():
                self._vai(u)
            if not self._amazon_bloccato():
                url = u
                break
            self.log(f"   Amazon: captcha al tentativo {i + 1}/{len(tentativi)}")
            time.sleep(random.uniform(6, 12))
        else:
            return {"url": url, "titolo": "", "modello": "", "img": "", "marca": "", "prezzo": "", "errore": "captcha Amazon"}
        titolo = ""
        try:
            titolo = self.page.locator("#productTitle, #title").first.inner_text(timeout=5000).strip()
        except Exception:
            pass
        modello = ""
        try:
            righe = self.page.locator("tr, #detailBullets_feature_div li, #productDetails_techSpec_section_1 tr").all_inner_texts()
            for r in righe:
                r1 = re.sub(r"[\u200e\u200f]", "", r)
                for et in MODELLO_ETICHETTE:
                    if r1.strip().lower().startswith(et.lower()):
                        modello = re.split(r"[\t:\n]", r1.strip()[len(et):].strip(" :\t\n"))[0].strip()
                        break
                if modello:
                    break
        except Exception:
            pass
        marca = ""
        try:  # riga "Marca" della scheda tecnica, altrimenti il link "Visita lo Store di ..."
            for r in self.page.locator("tr, #detailBullets_feature_div li, #productOverview_feature_div tr").all_inner_texts():
                r1 = re.sub(r"[\u200e\u200f]", "", r).strip()
                mm = re.match(r"(?:Marchio|Marca|Marke|Marque|Brand)\s*[:\t\n]+\s*(.+)", r1, re.I)
                if mm:
                    marca = mm.group(1).split("\n")[0].strip()
                    break
            if not marca:
                by = self.page.locator("#bylineInfo").first.inner_text(timeout=2000)
                mm = re.search(r"(?:Store di|Store von|boutique|Store de|Visit the)\s+(.+?)(?:\s+Store)?$", by.strip(), re.I) or \
                    re.search(r"(?:Marchio|Marca|Marke|Marque|Brand)\s*:\s*(.+)", by, re.I)
                marca = mm.group(1).strip() if mm else ""
        except Exception:
            pass
        prezzo = ""
        try:
            prezzo = self.page.locator("#corePrice_feature_div .a-offscreen, #corePriceDisplay_desktop_feature_div .a-offscreen, "
                                       "#apex_desktop .a-offscreen, .a-price .a-offscreen").first.inner_text(timeout=3000).strip()
        except Exception:
            pass
        img = ""
        try:
            el = self.page.locator("#landingImage, #imgTagWrapperId img, #main-image").first
            img = el.get_attribute("data-old-hires", timeout=2000) or el.get_attribute("src", timeout=2000) or ""
        except Exception:
            pass
        return {"url": url, "titolo": titolo, "modello": modello, "img": img, "marca": marca, "prezzo": prezzo,
                "scheda": self.scheda(), "errore": "" if titolo else "titolo non trovato"}

    def cerca_web(self, asin):
        """Piano B quando Amazon blocca: cerca l'ASIN su un motore di ricerca e ritorna i titoli trovati."""
        titoli = []
        for url in (f"https://html.duckduckgo.com/html/?q={asin}",
                    f"https://www.bing.com/search?q=%22{asin}%22&setlang=it"):
            try:
                self._vai(url)
                self._pausa(1, 2)
                titoli += self.page.evaluate("""() => [...document.querySelectorAll(
                    '.result__title, .result__snippet, li.b_algo h2, li.b_algo p')].map(e => e.innerText).slice(0, 20)""")
            except Exception:
                continue
            if titoli:
                break
        return titoli

    # ------------------------------------------------------------ Retailer
    def cerca(self, url_template, query):
        url = url_template.replace("{q}", quote_plus(query))
        if url in self._ricerche:  # stessa ricerca già fatta per un altro ASIN (es. "Xiaomi 65 LED")
            return self._ricerche[url]
        self.riscalda(url)
        r = self._vai(url)
        if r is not None and r.status in (403, 429) or self._in_verifica():
            # bloccato: ripasso dalla home e riprovo una volta
            self._riscaldati.discard(re.match(r"(https?://[^/]+)", url).group(1))
            self.riscalda(url)
            r = self._vai(url)
        if r is None:
            return url, [], "timeout"
        self._pausa(0.5, 1.2)
        try:
            links = self.page.evaluate(JS_LINKS)
        except Exception as e:
            return url, [], f"errore lettura: {e}"
        visti, out = set(), []
        for l in links:
            h = l["href"].split("#")[0]
            base = h.split("?")[0].rstrip("/")
            if not re.search(r"\d{5,}|\.html$", base):  # il prodotto potrebbe essere nei parametri: chiave completa
                base = h
            if base in visti or not h.startswith("http") or re.search(r"\.(pdf|jpe?g|png|webp)$", base, re.I):
                continue  # stessa pagina con parametri diversi, o allegati (etichetta energetica, foto)
            visti.add(base)
            out.append({"url": urljoin(url, h), "testo": l["testo"],
                        "img": urljoin(url, l.get("img") or "") if l.get("img") else ""})
        stato = f"HTTP {r.status}" if r.status >= 400 else "ok"
        if stato == "ok":
            self._ricerche[url] = (url, out, stato)
        return url, out, stato

    # ------------------------------------------------------------ idealo (ponte quando il retailer non è leggibile)
    def idealo_cerca(self, dominio, query):
        """Cerca su idealo e ritorna i link prodotto [{url, testo}]."""
        base = f"https://www.{dominio}"
        if dominio not in self._idealo_azione:
            self._vai(base + "/")
            try:
                azione = self.page.evaluate("""() => { const i = document.querySelector('form input[name=q]');
                                               return i && i.form ? i.form.action : ''; }""")
            except Exception:
                azione = ""
            self._idealo_azione[dominio] = azione or base + "/MainSearchProductCategory.html"
        url = f"{self._idealo_azione[dominio]}?q={quote_plus(query)}"
        r = self._vai(url)
        if r is None or r.status >= 400:
            return []
        links = self.page.evaluate(JS_LINKS)
        visti, out = set(), []
        for l in links:
            h = l["href"].split("#")[0]
            # pagina prodotto idealo: contiene un id numerico lungo (es. /confronta-prezzi/209962597/...)
            if h in visti or dominio not in h or not re.search(r"/\d{6,}[/_]", h) or "relocator" in h:
                continue
            visti.add(h)
            out.append({"url": h, "testo": l["testo"]})
        return out

    def idealo_offerte(self, url):
        """Offerte di una pagina prodotto idealo: [{url, negozio, testo, prezzo, img}]."""
        r = self._vai(url)
        if r is None or r.status >= 400:
            return []
        try:
            return self.page.evaluate(JS_OFFERTE)
        except Exception:
            return []

    def verifica(self, url):
        """Apre la pagina prodotto: ritorna (vivo, titolo+h1, testo pagina, immagine, scheda tecnica).
        Le pagine lette negli ultimi 30 giorni vengono riusate senza riaprirle."""
        noto = self._cache.get("p:" + url)
        if noto:
            return True, noto.get("titolo", ""), noto.get("testo", ""), noto.get("img", ""), noto.get("scheda", {})
        r = self.riscalda(url) or self._vai(url)
        if r is None or r.status >= 400 or self._in_verifica():
            stato = None if r is None else (403 if self._in_verifica() else r.status)
            return False, "", "", "", {"_stato": stato}
        try:
            h1 = " ".join(self.page.locator("h1").all_inner_texts()[:2])
        except Exception:
            h1 = ""
        try:
            corpo = self.page.evaluate("() => document.body.innerText.slice(0, 30000)")
        except Exception:
            corpo = ""
        try:
            img = self.page.evaluate("""() => { const m = document.querySelector('meta[property="og:image"]');
                                       return m ? m.content : ''; }""")
        except Exception:
            img = ""
        titolo, sch = f"{self.page.title()} {h1}", self.scheda()
        # in cache solo l'essenziale: titolo, scheda e le funzioni HDR/HDMI trovate nel testo
        funzioni = " ".join(f for f in ("DOLBY VISION", "HDR10+", "HDMI 2.1") if f.replace(" ", "") in re.sub(r"\s", "", corpo.upper()))
        self.cache_put("p:" + url, {"titolo": titolo[:300], "img": img, "scheda": sch, "testo": funzioni})
        return True, titolo, corpo, img, sch

    def scheda(self):
        try:
            return self.page.evaluate(JS_SCHEDA) or {}
        except Exception:
            return {}
