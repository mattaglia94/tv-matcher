"""Regole deterministiche per riconoscere un TV dal nome/codice modello
e decidere se due TV sono "simili" (stessa famiglia, stesso pollice, codice diverso).

Nessuna AI: solo espressioni regolari e tabelle.
Le regole di famiglia per LG, Hisense e Samsung seguono il documento di matching.
"""
import re
from dataclasses import dataclass, field

MARCHE = ["LG", "HISENSE", "SAMSUNG", "TCL", "PHILIPS", "SONY", "PANASONIC",
          "XIAOMI", "TOSHIBA", "SHARP", "METZ", "GRUNDIG", "TELEFUNKEN", "THOMSON", "VIDAA"]


@dataclass
class InfoTV:
    testo: str = ""
    marca: str = ""
    codice: str = ""          # codice modello grezzo trovato (es. 55E7Q, OLED65C64LA)
    core: str = ""            # codice normalizzato per confronto "stesso modello"
    pollici: int | None = None
    tecnologia: str = ""      # OLED / MINILED / NEOQLED / QLED / LED
    famiglia: str = ""        # chiave di famiglia/fascia (es. HISENSE-QLED-ENTRY-1)
    pro: bool = False
    risoluzione: str = ""     # 8K / 4K / FHD / HD
    hz: int | None = None
    anno: int | None = None
    regola: str = ""          # quale regola ha classificato
    dolby_vision: bool = False
    hdr10plus: bool = False
    hdmi21: bool = False
    note: list = field(default_factory=list)


# ----------------------------------------------------------------- utilità
def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").upper().replace("”", '"').replace("″", '"')).strip()


def trova_marca(t: str) -> str:
    T = _norm(t)
    for m in MARCHE:
        if re.search(rf"\b{m}\b", T):
            return m
    return ""


def trova_pollici_testo(t: str) -> int | None:
    T = _norm(t)
    m = re.search(r"\b(\d{2,3})\s?(?:\"|POLLICI|POLL\.|INCH|ZOLL|PULGADAS|POUCES|'')", T)
    if m:
        return int(m.group(1))
    m = re.search(r"\((\d{2,3})\s?\"?\)", T)
    return int(m.group(1)) if m else None


def trova_risoluzione(t: str) -> str:
    T = _norm(t)
    if re.search(r"\b8K\b", T):
        return "8K"
    if re.search(r"\b(4K|UHD|ULTRA HD|2160P)\b", T):
        return "4K"
    if re.search(r"\b(FULL HD|FHD|1080P)\b", T):
        return "FHD"
    if re.search(r"\b(HD READY|HD|720P)\b", T):
        return "HD"
    return ""


def trova_hz(t: str) -> int | None:
    vals = [int(x) for x in re.findall(r"\b(\d{2,3})\s?HZ\b", _norm(t))]
    vals = [v for v in vals if 50 <= v <= 300]
    return max(vals) if vals else None


def classe_hz(hz):
    if hz is None:
        return None
    if hz <= 60:
        return 60
    if hz <= 120:
        return 120
    return 144


def trova_anno_testo(t: str) -> int | None:
    m = re.findall(r"\b(20[2-3]\d)\b", _norm(t))
    return int(m[-1]) if m else None


def tecnologia_testo(t: str) -> str:
    T = _norm(t)
    if "OLED" in T and "QLED" not in T:
        return "OLED"
    if re.search(r"MINI[\s-]?LED|MINILED|QD[\s-]?MINI", T):
        return "MINILED"
    if "NEO QLED" in T or "NEOQLED" in T:
        return "NEOQLED"
    if "QLED" in T or "QNED" in T:
        return "QLED"
    if "LED" in T or "LCD" in T:
        return "LED"
    return ""


# ----------------------------------------------------------------- LG
_LG_FAM = [  # (regex sul codice, tecnologia, famiglia)
    (r"OLEDG", "OLED", "LG-OLED-PREMIUM"),
    (r"OLEDC", "OLED", "LG-OLED-MID"),
    (r"OLEDB", "OLED", "LG-OLED-ENTRY"),
    (r"QNED9[23]", "MINILED", "LG-MINILED-PREMIUM"),
    (r"QNED8[56]", "MINILED", "LG-MINILED-ENTRY"),
    (r"QNED8[0124]", "QLED", "LG-QLED-ENTRY"),
    (r"NANO", "LED", "LG-UHD-PREMIUM"),
    (r"UA7", "LED", "LG-UHD-ENTRY"),
]


def _lg(T: str, info: InfoTV):
    # OLED: OLED65C64LA  /  altri: 65QNED86A6A, 65NANO81T6A, 55UA73006LA
    m = re.search(r"\bOLED(\d{2,3})([A-Z])(\d)([A-Z0-9]*)", T)
    if m:
        info.codice = m.group(0)
        info.pollici = int(m.group(1))
        info.core = f"OLED{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)[:1]}"  # es. OLED65C64
        key = "OLED" + m.group(2)
        anno_cifra = int(m.group(3))
        info.anno = 2020 + anno_cifra if anno_cifra <= 9 else None
    else:
        m = re.search(r"\b(\d{2,3})((?:QNED|NANO|UA|UT|UR|UQ)\d{1,2})([A-Z0-9]*)", T)
        if not m:
            return False
        info.codice = m.group(0)
        info.pollici = int(m.group(1))
        info.core = m.group(1) + m.group(2)
        key = m.group(2)
    for rx, tec, fam in _LG_FAM:
        if re.match(rx, key) or re.search(rx, info.codice):
            info.tecnologia, info.famiglia, info.regola = tec, fam, "LG"
            return True
    info.regola = "LG-sconosciuta"
    return True


# ----------------------------------------------------------------- Hisense
_HIS_FAM = [  # ordine importante: PRO prima della versione base
    ("E7", True, "QLED", "HISENSE-QLED-PREMIUM"),
    ("U7", True, "MINILED", "HISENSE-MINILED-MID"),
    ("U8", None, "MINILED", "HISENSE-MINILED-PREMIUM"),
    ("U7", False, "MINILED", "HISENSE-MINILED-ENTRY"),
    ("E8", None, "MINILED", "HISENSE-MINILED-SUPERENTRY"),
    ("E7", False, "QLED", "HISENSE-QLED-ENTRY-1"),
    ("A7", None, "QLED", "HISENSE-QLED-ENTRY-2"),
    ("E6", None, "LED", "HISENSE-LED-4K-ENTRY"),
    ("A6", None, "LED", "HISENSE-LED-4K-ENTRY"),
    ("A5", None, "QLED", "HISENSE-QLED-HD"),
    ("A4", None, "LED", "HISENSE-LED-HD"),
]


def _hisense(T: str, info: InfoTV):
    # 55E7Q, 55E79Q, 65E7NQ PRO, 65U7NQ, 100U8NQ, 43A4N
    m = re.search(r"\b(\d{2,3})([AEU])(\d)([A-Z0-9]*)", T)
    if not m:
        return False
    info.codice = m.group(0)
    info.pollici = int(m.group(1))
    info.pro = bool(re.search(r"PRO\b", T[m.start():m.end() + 6]))
    info.core = m.group(0) + ("PRO" if info.pro else "")
    serie = m.group(2) + m.group(3)
    for s, pro, tec, fam in _HIS_FAM:
        if s == serie and (pro is None or pro == info.pro):
            info.tecnologia, info.famiglia, info.regola = tec, fam, "HISENSE"
            return True
    info.regola = "HISENSE-sconosciuta"
    return True


# ----------------------------------------------------------------- Samsung
SAMSUNG_ANNO = {"H": 2026, "F": 2025, "D": 2024, "C": 2023, "B": 2022, "A": 2021}


def _samsung_fascia(n: int, tre_cifre: bool):
    if tre_cifre:  # 8K
        if n >= 990:
            return "8K-PREMIUM"
        if n >= 800:
            return "8K-MID"
        return "8K-ENTRY"
    if n > 94:
        return "4K-PREMIUM"
    if n >= 90:
        return "4K-MID"
    if n >= 80:
        return "4K-ENTRY"
    return "4K-SUPERENTRY"


def _samsung(T: str, info: InfoTV):
    # QE65QN90FATXZT, UE55U8000F, QE65S90F, QE55Q7F, TQ65QN80H
    m = re.search(r"\b(?:QE|UE|GQ|GU|TQ|TU|QN)?(\d{2,3})(QN|Q|S|U|M)(\d{1,4})([A-Z]?)([A-Z0-9]*)", T)
    if not m:
        return False
    info.codice = m.group(0)
    info.pollici = int(m.group(1))
    lett, num, anno_l = m.group(2), m.group(3), m.group(4)
    info.core = f"{m.group(1)}{lett}{num}{anno_l}"
    info.anno = SAMSUNG_ANNO.get(anno_l)
    n = int(num)
    tre = len(num) == 3
    if lett == "QN":
        info.tecnologia = "NEOQLED"
        info.famiglia = "SAMSUNG-NEOQLED-" + _samsung_fascia(n, tre)
    elif lett == "M":
        info.tecnologia = "MINILED"
        info.famiglia = "SAMSUNG-MINILED-" + _samsung_fascia(n, tre)
    elif lett == "S":
        info.tecnologia = "OLED"
        f = "SUPERPREMIUM" if n > 98 else "PREMIUM" if n >= 94 else "MID" if n >= 90 else "ENTRY"
        info.famiglia = "SAMSUNG-OLED-" + f
    elif lett == "Q":
        d = int(num[0])
        info.tecnologia = "QLED"
        info.famiglia = "SAMSUNG-QLED-PREMIUM" if d >= 8 else "SAMSUNG-QLED-ENTRY"
    elif lett == "U":
        d = int(num[0])
        info.tecnologia = "LED"
        info.famiglia = "SAMSUNG-UHD-ENTRY" if d >= 8 else "SAMSUNG-UHD-SUPERENTRY"
    info.regola = "SAMSUNG"
    return True


# ----------------------------------------------------------------- generica
def _generica(T: str, info: InfoTV):
    """Altre marche (TCL, Philips, Sony...): codice = primo token con pollici+lettere,
    famiglia = marca + tecnologia + serie letterale (es. TCL C7, PHILIPS PML9)."""
    m = re.search(r"\b(?:[A-Z]{1,4})?(\d{2,3})([A-Z]{1,4})(\d{1,4})([A-Z0-9]*)\b", T)
    if m:
        info.codice = m.group(0)
        info.pollici = info.pollici or int(m.group(1))
        info.core = m.group(1) + m.group(2) + m.group(3)
        serie = m.group(2) + m.group(3)[0]
    else:
        serie = ""
    info.tecnologia = tecnologia_testo(T)
    info.pro = " PRO" in T
    info.famiglia = f"{info.marca}-{info.tecnologia}-{serie}"
    info.regola = "GENERICA"
    return bool(m)


def analizza(testo: str, codice_noto: str = "") -> InfoTV:
    """Analizza titolo prodotto (+ eventuale codice modello già noto)."""
    T = _norm(f"{codice_noto} {testo}")
    info = InfoTV(testo=testo or "")
    info.marca = trova_marca(T)
    info.risoluzione = trova_risoluzione(T)
    info.hz = trova_hz(T)
    info.pollici = trova_pollici_testo(T)
    anno_t = trova_anno_testo(T)
    pollici_testo = info.pollici
    ok = False
    if info.marca == "LG":
        ok = _lg(T, info)
    elif info.marca == "HISENSE":
        ok = _hisense(T, info)
    elif info.marca == "SAMSUNG":
        ok = _samsung(T, info)
    if not ok:
        _generica(T, info)
    if pollici_testo and info.pollici != pollici_testo:
        info.note.append(f"pollici codice {info.pollici} ≠ titolo {pollici_testo}")
        info.pollici = pollici_testo
    if info.anno is None:
        info.anno = anno_t
    if not info.tecnologia:
        info.tecnologia = tecnologia_testo(T)
    if info.tecnologia == "OLED" and not info.risoluzione:
        info.risoluzione = "4K"
    info.dolby_vision = "DOLBY VISION" in T
    info.hdr10plus = bool(re.search(r"HDR\s?10\s?\+|HDR10 PLUS", T))
    info.hdmi21 = bool(re.search(r"HDMI\s?2\.1", T))
    return info


# ----------------------------------------------------------------- parametri
PARAMETRI_DEFAULT = {
    "pollici": {"attivo": True, "tolleranza": 0},
    "stessa_marca": {"attivo": True},
    "famiglia": {"attivo": True},
    "tecnologia": {"attivo": True, "equivalenze": [["MINILED", "NEOQLED"]]},
    "risoluzione": {"attivo": True},
    "refresh": {"attivo": True},
    "anno": {"attivo": True, "valore": 2026, "accetta_ignoto": True},
    "pro": {"attivo": True},
    "dolby_vision": {"attivo": False},
    "hdr10plus": {"attivo": False},
    "hdmi21": {"attivo": False},
    "max_match": 1,
    "verifica_url": True,
}


def unisci_parametri(p: dict | None) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PARAMETRI_DEFAULT.items()}
    for k, v in (p or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def _tec_equivalenti(a: str, b: str, gruppi) -> bool:
    if a == b:
        return True
    return any(a in g and b in g for g in (gruppi or []))


def confronta_param(amz: InfoTV, cand: InfoTV, P: dict):
    """Come confronta() ma ogni criterio si accende/spegne da P (vedi PARAMETRI_DEFAULT).
    Ritorna (ok, motivo, punteggio): punteggio più basso = più vicino."""
    if not cand.codice:
        return False, "codice modello non leggibile", 0
    if stesso_modello(amz, cand):
        return False, "stesso modello (escluso)", 0
    if P["stessa_marca"]["attivo"] and cand.marca != amz.marca:
        return False, "marca diversa", 0
    if not cand.marca:
        return False, "marca non riconosciuta", 0
    if P["pollici"]["attivo"]:
        tol = int(P["pollici"].get("tolleranza") or 0)
        if cand.pollici is None or amz.pollici is None or abs(cand.pollici - amz.pollici) > tol:
            return False, f"pollici {cand.pollici}", 0
    # la famiglia ha senso solo nella stessa marca
    if P["famiglia"]["attivo"] and cand.marca == amz.marca:
        if not cand.famiglia or cand.famiglia != amz.famiglia:
            return False, f"famiglia {cand.famiglia or '?'}", 0
    if P["tecnologia"]["attivo"]:
        if not cand.tecnologia or not _tec_equivalenti(amz.tecnologia, cand.tecnologia,
                                                       P["tecnologia"].get("equivalenze")):
            return False, f"tecnologia {cand.tecnologia or '?'}", 0
    if P["pro"]["attivo"] and cand.pro != amz.pro:
        return False, "PRO vs non-PRO", 0
    if P["risoluzione"]["attivo"] and amz.risoluzione and cand.risoluzione \
            and amz.risoluzione != cand.risoluzione:
        return False, f"risoluzione {cand.risoluzione}", 0
    if P["refresh"]["attivo"] and classe_hz(amz.hz) and classe_hz(cand.hz) \
            and classe_hz(amz.hz) != classe_hz(cand.hz):
        return False, f"refresh {cand.hz}Hz", 0
    # Dolby Vision / HDR10+ / HDMI 2.1 si controllano sulla pagina prodotto (nucleo.elabora_asin)
    nota = ""
    if P["anno"]["attivo"]:
        target = int(P["anno"].get("valore") or 2026)
        if cand.anno is not None and cand.anno != target:
            return False, f"anno {cand.anno}", 0
        if cand.anno is None:
            if not P["anno"].get("accetta_ignoto", True):
                return False, "anno non determinabile", 0
            nota = "anno da verificare"
    na = re.findall(r"\d+", amz.core[len(str(amz.pollici or "")):]) or ["0"]
    nb = re.findall(r"\d+", cand.core[len(str(cand.pollici or "")):]) or ["0"]
    score = abs(int(na[0]) - int(nb[0]))
    score += 0 if cand.marca == amz.marca else 1000
    score += 0 if cand.pollici == amz.pollici else 100 * abs((cand.pollici or 0) - (amz.pollici or 0))
    score += 5 if nota else 0
    return True, nota or "ok", score


# ----------------------------------------------------------------- matching
def stesso_modello(a: InfoTV, b: InfoTV) -> bool:
    if not a.core or not b.core:
        return False
    x, y = a.core, b.core
    return x == y or x in b.codice or y in a.codice


def confronta(amz: InfoTV, cand: InfoTV, anno_target: int, accetta_anno_ignoto: bool):
    """Ritorna (ok, motivo, punteggio). Punteggio più basso = più vicino."""
    if not cand.marca or cand.marca != amz.marca:
        return False, "marca diversa", 0
    if cand.pollici != amz.pollici:
        return False, f"pollici {cand.pollici}", 0
    if stesso_modello(amz, cand):
        return False, "stesso modello (escluso)", 0
    if not cand.famiglia or cand.famiglia != amz.famiglia:
        return False, f"famiglia {cand.famiglia or '?'}", 0
    if cand.pro != amz.pro:
        return False, "PRO vs non-PRO", 0
    if amz.risoluzione and cand.risoluzione and amz.risoluzione != cand.risoluzione:
        return False, f"risoluzione {cand.risoluzione}", 0
    if classe_hz(amz.hz) and classe_hz(cand.hz) and classe_hz(amz.hz) != classe_hz(cand.hz):
        return False, f"refresh {cand.hz}Hz", 0
    nota = ""
    if cand.anno is not None and cand.anno != anno_target:
        return False, f"anno {cand.anno}", 0
    if cand.anno is None:
        if not accetta_anno_ignoto:
            return False, "anno non determinabile", 0
        nota = "anno da verificare"
    # vicinanza: differenza numerica tra i codici serie
    na = re.findall(r"\d+", amz.core[len(str(amz.pollici)):]) or ["0"]
    nb = re.findall(r"\d+", cand.core[len(str(cand.pollici)):]) or ["0"]
    score = abs(int(na[0]) - int(nb[0])) + (5 if nota else 0)
    return True, nota or "ok", score
