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


class Browser:
    def __init__(self, visibile=False, log=print):
        self.log = log
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
        self.page = self.ctx.new_page()
        self._cookie_ok = set()

    def chiudi(self):
        try:
            self.b.close()
            self.pw.stop()
        except Exception:
            pass

    def _pausa(self, a=1.5, b=3.5):
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
        try:
            self.page.wait_for_load_state("networkidle", timeout=12000)
        except PWTimeout:
            pass
        dominio = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        self._cookie(dominio)
        for _ in range(4):  # scroll per caricare i prodotti "lazy"
            self.page.mouse.wheel(0, 2500)
            time.sleep(0.6)
        return r

    # ------------------------------------------------------------ Amazon
    def amazon(self, asin, dominio):
        url = f"https://www.{dominio}/dp/{asin}"
        self._vai(url)
        self._pausa()
        html = self.page.content()
        if "captcha" in html.lower() and "productTitle" not in html:
            return {"url": url, "titolo": "", "modello": "", "img": "", "errore": "captcha Amazon"}
        titolo = ""
        try:
            titolo = self.page.locator("#productTitle").first.inner_text(timeout=5000).strip()
        except Exception:
            pass
        modello = ""
        try:
            righe = self.page.locator("tr, #detailBullets_feature_div li").all_inner_texts()
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
        img = ""
        try:
            el = self.page.locator("#landingImage, #imgTagWrapperId img").first
            img = el.get_attribute("data-old-hires", timeout=2000) or el.get_attribute("src", timeout=2000) or ""
        except Exception:
            pass
        return {"url": url, "titolo": titolo, "modello": modello, "img": img,
                "errore": "" if titolo else "titolo non trovato"}

    # ------------------------------------------------------------ Retailer
    def cerca(self, url_template, query):
        url = url_template.replace("{q}", quote_plus(query))
        r = self._vai(url)
        if r is None:
            return url, [], "timeout"
        self._pausa(1, 2.5)
        try:
            links = self.page.evaluate(JS_LINKS)
        except Exception as e:
            return url, [], f"errore lettura: {e}"
        visti, out = set(), []
        for l in links:
            h = l["href"].split("#")[0]
            if h in visti or not h.startswith("http"):
                continue
            visti.add(h)
            out.append({"url": urljoin(url, h), "testo": l["testo"],
                        "img": urljoin(url, l.get("img") or "") if l.get("img") else ""})
        stato = f"HTTP {r.status}" if r.status >= 400 else "ok"
        return url, out, stato

    def verifica(self, url):
        """Apre la pagina prodotto: ritorna (vivo, titolo+h1, testo pagina, immagine)."""
        r = self._vai(url)
        if r is None or r.status >= 400:
            return False, "", "", ""
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
        return True, f"{self.page.title()} {h1}", corpo, img
