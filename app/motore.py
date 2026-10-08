"""Flusso completo: legge input Excel -> Amazon -> retailer -> scrive output Excel."""
import datetime as dt
import os
import re

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from regole import analizza, confronta
from config_default import AMAZON_DOMINIO, RETAILER

# ------------------------------------------------------------ query di ricerca
def query_ricerca(info):
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
    else:
        q.append(f"{m} {p} {info.tecnologia.replace('MINILED', 'Mini LED')}".strip())
    q.append(f"TV {m} {p}")
    return q


# ------------------------------------------------------------ lettura input
def leggi_input(percorso):
    wb = load_workbook(percorso, data_only=True)
    ws = wb["ASIN"] if "ASIN" in wb.sheetnames else wb.worksheets[0]
    righe = []
    intest = [str(c.value or "").strip().lower() for c in ws[1]]

    def col(*nomi):
        for n in nomi:
            if n in intest:
                return intest.index(n)
        return None
    c_asin = col("asin")
    c_nome = col("amazon product name", "nome prodotto amazon", "item name")
    c_mod = col("amazon model", "modello amazon")
    c_paese = col("paese", "country")
    start = 2
    if c_asin is None:  # foglio senza intestazione: ASIN in colonna A
        c_asin, start = 0, 1
    for r in ws.iter_rows(min_row=start, values_only=True):
        a = str(r[c_asin] or "").strip().upper()
        if not re.fullmatch(r"B0[A-Z0-9]{8}", a):
            continue
        righe.append({"asin": a,
                      "nome": str(r[c_nome] or "").strip() if c_nome is not None else "",
                      "modello": str(r[c_mod] or "").strip() if c_mod is not None else "",
                      "paese": str(r[c_paese] or "").strip().upper() if c_paese is not None else ""})
    retailer = []
    if "Retailer" in wb.sheetnames:
        for r in wb["Retailer"].iter_rows(min_row=2, values_only=True):
            if r and r[0] and r[1] and r[2]:
                retailer.append((str(r[0]).strip().upper(), str(r[1]).strip(), str(r[2]).strip(),
                                 str(r[3] or "SI").strip().upper()))
    impost = {"anno": 2026, "anno_ignoto": True, "verifica": True}
    if "Impostazioni" in wb.sheetnames:
        for r in wb["Impostazioni"].iter_rows(min_row=2, values_only=True):
            if not r or not r[0]:
                continue
            k, v = str(r[0]).lower(), r[1]
            if "anno target" in k:
                impost["anno"] = int(v)
            elif "anno non" in k:
                impost["anno_ignoto"] = str(v).upper().startswith("S")
            elif "verifica" in k:
                impost["verifica"] = str(v).upper().startswith("S")
    return righe, retailer or list(RETAILER), impost


# ------------------------------------------------------------ esecuzione
def esegui(percorso_input, paese, cartella_out, visibile=False, log=print, stop=lambda: False):
    from browser import Browser
    righe, retailer, imp = leggi_input(percorso_input)
    paese = paese.upper()
    ret = [(n, u) for (p, n, u, att) in retailer if p == paese and att.startswith("S")]
    righe = [r for r in righe if not r["paese"] or r["paese"] == paese]
    log(f"{len(righe)} ASIN, {len(ret)} retailer per {paese}: {', '.join(n for n, _ in ret)}")
    if not righe or not ret:
        raise RuntimeError("Nessun ASIN o nessun retailer attivo per il paese scelto.")

    br = Browser(visibile=visibile, log=log)
    risultati, dettaglio = [], []
    try:
        for i, r in enumerate(righe, 1):
            if stop():
                break
            log(f"[{i}/{len(righe)}] {r['asin']}")
            nota_amz = ""
            if not r["nome"] or not r["modello"]:
                a = br.amazon(r["asin"], AMAZON_DOMINIO.get(paese, "amazon.it"))
                r["nome"] = r["nome"] or a["titolo"]
                r["modello"] = r["modello"] or a["modello"]
                nota_amz = a["errore"]
            info = analizza(r["nome"], r["modello"])
            r["info"] = info
            r["modello_out"] = info.codice or r["modello"]
            log(f"   Amazon: {info.marca} {info.codice} {info.pollici}\" {info.famiglia} "
                f"{'PRO ' if info.pro else ''}{nota_amz}")
            dettaglio.append([r["asin"], "Amazon", r["modello_out"], info.famiglia, info.pollici,
                              info.anno, "", nota_amz or "riferimento", ""])
            r["match"] = {}
            if not info.marca or not info.pollici:
                log("   ⚠ modello Amazon non riconosciuto: compila 'Amazon Model' nel file input")
                continue
            for nome_r, url_t in ret:
                if stop():
                    break
                validi = {}
                for q in query_ricerca(info):
                    url_s, links, stato = br.cerca(url_t, q)
                    if stato != "ok":
                        dettaglio.append([r["asin"], nome_r, "", "", "", "", url_s, f"ricerca: {stato}", q])
                    for l in links:
                        c = analizza(l["testo"])
                        if c.marca != info.marca or c.pollici != info.pollici:
                            continue
                        ok, motivo, score = confronta(info, c, imp["anno"], imp["anno_ignoto"])
                        dettaglio.append([r["asin"], nome_r, c.codice, c.famiglia, c.pollici, c.anno,
                                          l["url"], ("VALIDO " if ok else "scartato: ") + motivo, q])
                        if ok and l["url"] not in validi:
                            validi[l["url"]] = (score, c)
                    if validi:
                        break
                scelta = None
                for url, (score, c) in sorted(validi.items(), key=lambda x: x[1][0]):
                    if imp["verifica"]:
                        vivo, testo_pag = br.verifica(url)
                        if not vivo:
                            dettaglio.append([r["asin"], nome_r, c.codice, "", "", "", url, "URL non attivo", ""])
                            continue
                        cp = analizza(testo_pag)
                        if cp.codice and cp.pollici and cp.pollici != info.pollici:
                            dettaglio.append([r["asin"], nome_r, c.codice, "", "", "", url,
                                              "pagina prodotto non coerente", ""])
                            continue
                    scelta = (c.codice, url)
                    break
                r["match"][nome_r] = scelta
                log(f"   {nome_r}: {scelta[0] if scelta else '—'}")
    finally:
        br.chiudi()
    return scrivi_output(righe, [n for n, _ in ret], dettaglio, paese, cartella_out)


# ------------------------------------------------------------ output
def scrivi_output(righe, nomi_ret, dettaglio, paese, cartella_out):
    wb = Workbook()
    ws = wb.active
    ws.title = f"Matching {paese}"
    blu = PatternFill("solid", fgColor="1F4E78")
    azz = PatternFill("solid", fgColor="DDEBF7")
    bianco = Font(bold=True, color="FFFFFF")
    ws.append(["ASIN", "Amazon product name", "Amazon Model"] +
              [x for n in nomi_ret for x in (n, "")])
    ws.append(["", "", ""] + [x for _ in nomi_ret for x in ("Model Name", "Product URL")])
    for c in range(1, 4):
        ws.merge_cells(start_row=1, start_column=c, end_row=2, end_column=c)
    for i, _ in enumerate(nomi_ret):
        c = 4 + 2 * i
        ws.merge_cells(start_row=1, start_column=c, end_row=1, end_column=c + 1)
    for row in ws.iter_rows(min_row=1, max_row=2):
        for cell in row:
            cell.font = bianco if cell.row == 1 else Font(bold=True)
            cell.fill = blu if cell.row == 1 else azz
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in righe:
        riga = [r["asin"], r["nome"], r.get("modello_out", "")]
        for n in nomi_ret:
            m = (r.get("match") or {}).get(n)
            riga += [m[0], m[1]] if m else ["", ""]
        ws.append(riga)
        rr = ws.max_row
        for i, n in enumerate(nomi_ret):
            cell = ws.cell(rr, 5 + 2 * i)
            if cell.value:
                cell.hyperlink = cell.value
                cell.font = Font(color="0563C1", underline="single")
    ws.column_dimensions["A"].width = 13
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 18
    for i in range(len(nomi_ret)):
        ws.column_dimensions[get_column_letter(4 + 2 * i)].width = 18
        ws.column_dimensions[get_column_letter(5 + 2 * i)].width = 45
    ws.freeze_panes = "D3"

    wd = wb.create_sheet("Dettaglio")
    wd.append(["ASIN", "Fonte", "Modello trovato", "Famiglia", "Pollici", "Anno", "URL", "Esito", "Ricerca"])
    for c in wd[1]:
        c.font, c.fill = bianco, blu
    for d in dettaglio:
        wd.append(d)
    wd.auto_filter.ref = wd.dimensions
    for col, w in zip("ABCDEFGHI", (13, 16, 18, 30, 8, 7, 60, 34, 26)):
        wd.column_dimensions[col].width = w

    os.makedirs(cartella_out, exist_ok=True)
    nome = f"Matching_TV_{paese}_{dt.datetime.now():%Y-%m-%d_%H%M}.xlsx"
    out = os.path.join(cartella_out, nome)
    wb.save(out)
    return out


def crea_modello_input(percorso):
    """Crea il file di input vuoto con i 3 fogli."""
    wb = Workbook()
    ws = wb.active
    ws.title = "ASIN"
    ws.append(["ASIN", "Paese", "Amazon product name", "Amazon Model"])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["C"].width = 60
    ws.column_dimensions["D"].width = 18
    wr = wb.create_sheet("Retailer")
    wr.append(["Paese", "Nome retailer", "URL ricerca ({q} = testo cercato)", "Attivo (SI/NO)"])
    for c in wr[1]:
        c.font = Font(bold=True)
    for r in RETAILER:
        wr.append(list(r))
    wr.column_dimensions["B"].width = 20
    wr.column_dimensions["C"].width = 75
    wi = wb.create_sheet("Impostazioni")
    wi.append(["Impostazione", "Valore", "Spiegazione"])
    wi.append(["Anno target", 2026, "Solo modelli di quest'anno"])
    wi.append(["Accetta anno non determinabile", "SI",
               "SI = accetta modelli il cui anno non si ricava dal codice/titolo (segnalati nel foglio Dettaglio)"])
    wi.append(["Verifica pagina prodotto", "SI", "SI = apre ogni URL scelto per controllare che sia attivo"])
    for c in wi[1]:
        c.font = Font(bold=True)
    wi.column_dimensions["A"].width = 32
    wi.column_dimensions["C"].width = 90
    wb.save(percorso)
