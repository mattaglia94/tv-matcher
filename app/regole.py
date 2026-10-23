"""Regole deterministiche per riconoscere un TV dal nome/codice modello
e decidere se due TV sono "simili" (stessa famiglia, stesso pollice, codice diverso).

Nessuna AI: solo espressioni regolari e tabelle.
Le regole di famiglia per LG, Hisense e Samsung seguono il documento di matching.
"""
import json
import os
import re
import sys
from dataclasses import dataclass, field


# ----------------------------------------------------------------- catalogo marche e serie
# Il catalogo predefinito è web/catalogo.json (lo stesso file che mostra il sito).
# Le modifiche fatte dal sito vengono salvate a parte e passate a imposta_catalogo():
# una marca modificata sostituisce quella predefinita, una marca con "rimossa": true la toglie.
def _percorsi_catalogo():
    qui = os.path.dirname(os.path.abspath(__file__))
    yield os.path.join(qui, "..", "web", "catalogo.json")
    yield os.path.join(getattr(sys, "_MEIPASS", qui), "catalogo.json")
    yield os.path.join(os.path.dirname(sys.executable), "catalogo.json")


def catalogo_predefinito() -> dict:
    for p in _percorsi_catalogo():
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return {"marche": []}


def unisci_catalogo(base: dict, utente: dict | None) -> dict:
    out = {k: v for k, v in base.items() if k != "marche"}
    marche = {m["marca"].upper(): m for m in base.get("marche", [])}
    for m in (utente or {}).get("marche", []):
        k = (m.get("marca") or "").upper()
        if not k:
            continue
        if m.get("rimossa"):
            marche.pop(k, None)
        else:
            marche[k] = m
    out["marche"] = list(marche.values())
    return out


_CAT = {"marche": [], "alias": []}


def imposta_catalogo(catalogo: dict):
    """Prepara il catalogo per la ricerca: marche indicizzate e alias ordinati dal più lungo."""
    marche, alias = {}, []
    for m in catalogo.get("marche", []):
        nome = _norm(m["marca"])
        marche[nome] = m
        for a in set([nome] + [_norm(x) for x in m.get("alias", []) if x]):
            alias.append((a, nome))
    alias.sort(key=lambda x: -len(x[0]))
    _CAT.update({"marche": marche, "alias": alias, "fonte": catalogo})


def marche_note():
    return list(_CAT["marche"].keys())


@dataclass
class InfoTV:
    testo: str = ""
    marca: str = ""
    codice: str = ""          # codice modello grezzo trovato (es. 55E7Q, OLED65C64LA)
    core: str = ""            # codice normalizzato per confronto "stesso modello"
    pollici: int | None = None
    tecnologia: str = ""      # OLED / MINILED / NEOQLED / QLED / LED
    famiglia: str = ""        # chiave di famiglia/fascia (es. HISENSE-QLED-ENTRY-1)
    fascia: str = ""          # fascia comune a tutte le marche: BASE / ENTRY / MID / PREMIUM / TOP
    pro: bool = False
    risoluzione: str = ""     # 8K / 4K / FHD / HD
    hz: int | None = None
    anno: int | None = None
    regola: str = ""          # quale regola ha classificato
    chiave: str = ""          # serie ricavata dal codice (es. QN90, OLEDC, C7, BRAVIA 8): si cerca nel catalogo
    fascia_fonte: str = ""    # catalogo / marca (predefinita della marca) / stimata (dal prezzo)
    marca_nuova: bool = False # marca non presente nel catalogo (ricavata da Amazon)
    dolby_vision: bool = False
    hdr10plus: bool = False
    hdmi21: bool = False
    note: list = field(default_factory=list)


# ----------------------------------------------------------------- utilità
def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").upper().replace("”", '"').replace("″", '"')).strip()


def trova_marca(t: str) -> str:
    T = _norm(t)
    for a, nome in _CAT["alias"]:
        if re.search(rf"(?<![A-Z0-9]){re.escape(a)}(?![A-Z0-9])", T):
            return nome
    return ""


def marca_da_codice(t: str) -> str:
    """Se il testo non nomina la marca, la deduce dal formato del codice modello."""
    T = _norm(t)
    if re.search(r"\b(?:QE|UE|GQ|GU|TQ|TU)\d{2,3}[A-Z]", T):
        return "SAMSUNG"
    if re.search(r"\bOLED\d{2,3}[A-Z]\d|\b\d{2,3}(?:QNED|NANO)\d|\b\d{2,3}U[ATRQ]\d{2}", T):
        return "LG"
    if re.search(r"\b\d{2,3}[AEU][4-9][A-Z0-9]*\b", T):
        return "HISENSE"
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
    if re.search(r"\b(4K|UHD|ULTRA[\s-]?HD|2160P|3840\s?X\s?2160)\b", T):
        return "4K"
    if re.search(r"\b(FULL[\s-]?HD|FHD|1080P|1080\s?PIXEL|1920\s?X\s?1080)", T):
        return "FHD"
    if re.search(r"\b(HD[\s-]?READY|720P|1366\s?X\s?768)\b", T) or re.search(r"(?<!MPEG4 )(?<!MPEG-4 )\bHD\b(?![+-])", T):
        return "HD"
    return ""


_HZ_MARKETING = r"(?:GAME\s?BOOST|BOOST|MEMC|MOTION\s?RATE|MOTION|PMR|PQI|CMR|MCI|TRUMOTION|GAMING|DLG|VRR|FINO A|UP TO|BIS ZU|JUSQU)"


def trova_hz(t: str) -> int | None:
    """Frequenza NATIVA del pannello. Si ignorano i valori di marketing ("Game Boost 120Hz", "Motion Rate 240",
    "MEMC 120 Hz"), che non indicano la frequenza reale."""
    T = _norm(t)
    vals = []
    for m in re.finditer(r"\b(\d{2,3})\s?HZ\b", T):
        prima = T[max(0, m.start() - 25):m.start()]
        dopo = T[m.end():m.end() + 12]
        if re.search(_HZ_MARKETING + r"[^,;|()]*$", prima) or re.match(r"\s*(?:MEMC|MOTION|GAME|BOOST)", dopo):
            continue
        v = int(m.group(1))
        if 50 <= v <= 300:
            vals.append(v)
    return max(vals) if vals else None


def hz_diverse(a, b) -> bool:
    """Frequenze davvero diverse: 50/60 Hz contro 144 Hz e oltre. 60 vs 120 e 120 vs 144 non bastano a scartare:
    schede e titoli mescolano spesso frequenza nativa e valori di marketing (Game Boost, Motion Xcelerator, VRR)."""
    ca, cb = classe_hz(a), classe_hz(b)
    return bool(ca and cb) and {ca, cb} == {60, 144}


def classe_hz(hz):
    if hz is None:
        return None
    if hz <= 60:
        return 60
    if hz <= 120:
        return 120
    return 144


def trova_anno_testo(t: str) -> int | None:
    # il PRIMO anno è quello del nome del modello ("A Pro 75 2026 ... uscita 2025"): gli anni successivi
    # sono di solito data di lancio, etichetta energetica o altro
    m = re.findall(r"\b(20[2-3]\d)\b", _norm(t))
    return int(m[0]) if m else None


_RANGO_TEC = {"LED": 1, "QLED": 2, "MINILED": 3, "NEOQLED": 3, "OLED": 4}


def tecnologia_testo(t: str) -> str:
    T = _norm(t)
    if "OLED" in T and "QLED" not in T:
        return "OLED"
    if re.search(r"MINI[\s-]?LED|MINILED|QD[\s-]?MINI", T):
        return "MINILED"
    if "NEO QLED" in T or "NEOQLED" in T:
        return "NEOQLED"
    if "QLED" in T or "QNED" in T or "QUANTUM DOT" in T:
        return "QLED"
    if "LED" in T or "LCD" in T or "CRYSTAL UHD" in T:
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
    (r"QNED7", "QLED", "LG-QLED-ENTRY"),
    (r"NANO|NU\d", "LED", "LG-UHD-PREMIUM"),
    (r"UA7", "LED", "LG-UHD-ENTRY"),
    (r"U[A-Z]\d", "LED", "LG-UHD-ENTRY"),
]


_LG_ANNO = {"Q": 2022, "R": 2023, "T": 2024, "A": 2025, "B": 2026}


def _lg(T: str, info: InfoTV):
    # OLED: OLED65C64LA  /  altri: 65QNED86A6A, 65NANO81T6A, 55UA73006LA
    m = re.search(r"\bOLED(\d{2,3})([A-Z])(\d)([A-Z0-9]*)", T)
    if m:
        info.codice = m.group(0)
        info.pollici = int(m.group(1))
        info.core = f"OLED{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)[:1]}"  # es. OLED65C64
        key = "OLED" + m.group(2)
        info.chiave = key
        anno_cifra = int(m.group(3))
        info.anno = 2020 + anno_cifra if anno_cifra <= 9 else None
    else:
        m = re.search(r"\b(\d{2,3})((?:QNED|NANO|NU|UA|UT|UR|UQ|U[A-Z])\d{1,2})([A-Z0-9]*)", T)
        if not m:
            return False
        info.codice = m.group(0)
        info.pollici = int(m.group(1))
        info.core = m.group(1) + m.group(2)
        key = m.group(2)
        info.chiave = key
        # anno dalla lettera: serie U (UA7 = 2025) o lettera dopo la serie (QNED82A6 = 2025, NANO81T6 = 2024)
        lett = key[1] if re.match(r"U[A-Z]\d", key) else (m.group(3)[:1] if re.match(r"[A-Z]\d", m.group(3)) else "")
        info.anno = None if trova_anno_testo(T) else _LG_ANNO.get(lett)  # l'anno scritto nel titolo vince
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
    ("Q8", None, "MINILED", "HISENSE-MINILED-ENTRY-Q8"),
    ("U7", False, "MINILED", "HISENSE-MINILED-ENTRY"),
    ("E8", None, "MINILED", "HISENSE-MINILED-SUPERENTRY"),
    ("E7", False, "QLED", "HISENSE-QLED-ENTRY-1"),
    ("A7", None, "QLED", "HISENSE-QLED-ENTRY-2"),
    ("E6", None, "LED", "HISENSE-LED-4K-ENTRY-1"),
    ("A6", None, "LED", "HISENSE-LED-4K-ENTRY-2"),
    ("A5", None, "QLED", "HISENSE-QLED-HD"),
    ("A4", None, "LED", "HISENSE-LED-HD"),
]


# Metz (Skyworth): 40MQH7000Y, 32MQF7030Z, 60MNH7000Z, 43MUD7000Z -> pollici, M, tecnologia (Q/N/U/T), lettera anno
_METZ_ANNO = {"H": 2026, "F": 2025, "E": 2024, "D": 2023, "C": 2022}


def _metz(T: str, info: InfoTV):
    m = re.search(r"\b(\d{2,3})M([A-Z])([A-Z])(\d{4})([A-Z]?)\b", T)
    if not m:
        return False
    info.codice = m.group(0)
    info.pollici = int(m.group(1))
    info.core = m.group(0)
    info.chiave = "M" + m.group(2)
    if not trova_anno_testo(T):
        info.anno = _METZ_ANNO.get(m.group(3))
    return False  # il resto (tecnologia, fascia) lo completano catalogo e regole generiche


_HIS_ANNO = {"H": 2022, "K": 2023, "N": 2024, "Q": 2025, "S": 2026}


def _hisense(T: str, info: InfoTV):
    # 55E7Q, 55E79Q, 65E7NQ PRO, 65U7NQ, 100U8NQ, 43A4N
    m = re.search(r"\b(\d{2,3})([AEUQ])(\d)([A-Z0-9]*)", T)
    if not m:
        return False
    info.codice = m.group(0)
    info.pollici = int(m.group(1))
    info.pro = bool(re.search(rf"\b{re.escape(m.group(0))}[\s-]*PRO\b", T))
    info.core = m.group(0) + ("PRO" if info.pro else "")
    serie = m.group(2) + m.group(3)
    info.chiave = serie
    # anno dalla lettera finale: A6K 2023, E7NQ 2024, E7Q 2025, E7S/E7DS 2026
    for lettera in re.sub(r"[^A-Z]", "", m.group(4))[:3] if not trova_anno_testo(T) else "":  # l'anno scritto vince
        if lettera in _HIS_ANNO:
            info.anno = _HIS_ANNO[lettera]
            break
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
    m = re.search(r"\b(?:QE|UE|GQ|GU|TQ|TU|QN|MRE|MR)?-?(\d{2,3})(D?)(QN|LS|Q|S|U|M|R)(\d{1,4})([A-Z]?)([A-Z0-9]*)", T)
    if m and (not m.group(2) or m.group(3) == "U"):
        pol, lett, num, anno_l = m.group(1), m.group(3), m.group(4), m.group(5)
        if m.group(2):
            anno_l = "D"  # 75DU8079 = gamma 2024
        info.pollici = int(pol)
    else:
        # codice senza pollici, es. "Crystal UHD U8075F", "DU7179", "The Frame LS03F", "Q7F5"
        m = re.search(r"\bD?(QN|LS|Q|S|U|M|R)(\d{1,4})([A-H])(\d{0,3}|A[A-Z]?)\b", T) or \
            re.search(r"\b(U)(\d{4})()\b", T)  # U8005: serie Crystal senza lettera dell'anno
        if not m or not info.pollici or (m.group(1) == "S" and len(m.group(2)) < 2):
            return False
        pol, lett, num, anno_l = str(info.pollici), m.group(1), m.group(2), m.group(3)
        if lett == "U" and len(num) == 4 and m.group(0).startswith("D"):
            anno_l = "D"  # DU7179 = gamma 2024
    info.codice = m.group(0)
    info.core = f"{pol}{lett}{num}{anno_l}"
    if anno_l not in SAMSUNG_ANNO and m.lastindex >= 6 and (m.group(6) or "")[:1] in SAMSUNG_ANNO:
        anno_l = m.group(6)[0]  # M1EH: la lettera dell'anno è la seconda (E = variante)
    info.anno = SAMSUNG_ANNO.get(anno_l)
    n = int(num)
    tre = len(num) == 3
    info.chiave = ("8K-" if tre and lett in ("QN", "M") else "") + lett + num
    if lett in ("LS", "R"):
        info.tecnologia = "QLED" if lett == "LS" else "MINILED"
        info.famiglia = "SAMSUNG-" + ("LIFESTYLE" if lett == "LS" else "MICRO-RGB")
    elif lett in ("QN", "M"):
        info.tecnologia = "NEOQLED" if lett == "QN" else "MINILED"
        # serie a una cifra (M1EH, QN1EH, 2026) = linea nuova a sé, non confrontabile con M70/QN70
        info.famiglia = f"SAMSUNG-{info.tecnologia}-" + (f"SERIE{n}" if len(num) == 1 else _samsung_fascia(n, tre))
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


# ----------------------------------------------------------------- Xiaomi
def _xiaomi(T: str, info: InfoTV):
    """Xiaomi non usa codici modello nei titoli: il "codice" è serie + pollici
    (es. "TV F PRO 75" -> F PRO 75, core 75FPRO; anche dagli URL tipo pidXIA65FPRO).
    Famiglia: A e F (Google TV / Fire TV) sono la stessa fascia; S = Mini LED; MAX = grandi formati."""
    if re.search(r"\bL\d{2,3}M[A-Z]", T):  # codice ufficiale (L65MB-APEU): è il dato più affidabile
        return _xiaomi_codice(T, info)
    j = re.search(r"(?<![A-Z0-9-])(A|F|S|Q)(\d{2,3})(\s?PRO)?\b", T)    # "XIAOMI F65" (titoli Alcampo/Carrefour)
    if j and 24 <= int(j.group(2)) <= 115 and not re.search(r"CORTEX", T[max(0, j.start() - 8):j.start()]):
        T = T[:j.start()] + f"{j.group(1)}{' PRO' if j.group(3) else ''} {j.group(2)}" + T[j.end():]
    m = (re.search(r"\bXIA(\d{2,3})(A|F|S|MAX|Q)(PRO)?\d?\b", T)
         or re.search(r"\b(\d{2,3})(A|F|S|Q)(PRO)?\d?\b", T)           # codici tipo 50APRO2, 32A2 (titoli Unieuro)
         or re.search(r"\b(\d{2,3})\s+(A|F|S|MAX)(\s+PRO)?\b(?!\s*(?:CM|POLLICI|ZOLL|POUCES|PULGADAS|INCH))", T)  # "XIAOMI 43 F PRO 2026" (MediaWorld)
         or re.search(r"\b(?:TV\s+)?(A|F|S|MAX|Q\d?)(\s+PRO)?\s*(MINI\s?LED)?\b[^0-9]{0,20}?(\d{2,3})\b", T))
    if not m:
        return _xiaomi_codice(T, info) or _xiaomi_caratteristiche(T, info)
    if m.re.pattern.startswith("\\bXIA") or m.re.pattern.startswith("\\b(\\d"):
        poll, serie, pro = int(m.group(1)), m.group(2), bool(m.group(3))
    else:
        serie, pro, poll = m.group(1)[0] if m.group(1) != "MAX" else "MAX", bool(m.group(2)), int(m.group(4))
    if not 24 <= poll <= 115:
        return False
    info.pollici = info.pollici or poll
    info.pro = pro or bool(re.search(r"\bPRO\b", T))
    info.codice = f"{serie}{' PRO' if info.pro else ''} {info.pollici}"
    info.core = f"{info.pollici}{serie}{'PRO' if info.pro else ''}"
    # i 32"/40" HD della linea base formano una famiglia a sé; un PRO resta PRO anche se HD
    ris = trova_risoluzione(T) or ("HD" if info.pollici and info.pollici <= 32 else "")  # i 32" non sono mai 4K
    info.chiave = serie + ("-HD" if ris in ("HD", "FHD") and serie in ("A", "F") and not info.pro else "")
    info.tecnologia = tecnologia_testo(T) or ("MINILED" if serie == "S" else "QLED" if (info.pro or serie == "MAX") else "LED")
    fam = {"A": "AF", "F": "AF", "Q": "AF", "S": "S", "MAX": "MAX"}[serie]
    info.famiglia = f"XIAOMI-{info.tecnologia}-{fam}"
    info.fascia = "PREMIUM" if serie == "S" else "MID" if (info.pro or serie == "MAX") else "ENTRY"
    info.regola = "XIAOMI"
    return True


def _xiaomi_codice(T: str, info: InfoTV):
    """Codici Xiaomi ufficiali: L<pollici>M<lettera>[..]-<serie><P=Pro>..EU
    es. L75MB-APEU = 75" A Pro, L65MC-SEU = 65" S Mini LED, L43MB-FAVEU = 43" F (Fire TV)."""
    m = re.search(r"\bL(\d{2,3})M([A-Z])[A-Z0-9]{0,2}(?:-([A-Z]{2,6}))?", T)
    if not m:
        return False
    info.pollici = info.pollici or int(m.group(1))
    # NB: la lettera dopo "M" NON indica l'anno (L75MB-APEU è l'A Pro 75 2026, L65MB-FAEU l'F 65 2025):
    # l'anno si prende solo dal titolo
    info.anno = info.anno or trova_anno_testo(T)
    suff = m.group(3) or ""
    tec_t = tecnologia_testo(T)
    if suff[:1] in ("A", "F", "S", "Q"):
        serie = suff[0]
        info.pro = suff[1:2] == "P" or bool(re.search(r"\bPRO\b", T))
    else:  # codice senza suffisso: serie dal testo; un A/F QLED è sempre un PRO
        serie = "F" if "FIRE TV" in T else "A"
        info.pro = bool(re.search(r"\bPRO\b", T)) or tec_t == "QLED"
    info.codice = m.group(0)
    info.core = f"{info.pollici}{serie}{'PRO' if info.pro else ''}"
    info.tecnologia = tec_t or ("MINILED" if serie == "S" else "QLED" if info.pro else "LED")
    ris = trova_risoluzione(T) or ("HD" if info.pollici <= 32 else "")
    info.fascia = "PREMIUM" if serie == "S" else "MID" if info.pro else "BASE" if ris in ("HD", "FHD") else "ENTRY"
    info.famiglia = f"XIAOMI-{info.tecnologia}-{serie if serie == 'S' else 'AF'}{'-' + ris if ris in ('HD', 'FHD') and not info.pro else ''}"
    info.chiave = serie + ("-HD" if ris in ("HD", "FHD") and serie in ("A", "F") and not info.pro else "")
    info.regola = "XIAOMI-codice"
    return True


def _pollici_nudi(T: str):
    """Diagonale scritta senza unità ("QLED 65 Xiaomi"): primo numero da TV, escluse misure in cm/Hz/GB."""
    for m in re.finditer(r"\b(2[4-9]|[3-9]\d|1[01]\d)\b(?!\s?(?:CM|HZ|GB|W\b|%|MM|\.\d))", T):
        return int(m.group(1))
    return None


def _xiaomi_caratteristiche(T: str, info: InfoTV):
    """Xiaomi senza nome di serie né codice ufficiale (es. "TV QLED 65 Xiaomi ELA6760EU Fire TV"):
    la serie si ricava dalle caratteristiche. Mini LED = S, QLED = Pro, Fire TV = F, Google TV = A."""
    pol = info.pollici or _pollici_nudi(T)
    tec = tecnologia_testo(T)
    if not pol or not tec:
        return False
    if re.search(r"\bP1E?\b", T):
        serie = "P1"
    elif tec in ("MINILED", "NEOQLED"):
        serie = "S"
    else:
        serie = "F" if "FIRE TV" in T or "FIRE OS" in T else "A"
    info.pollici = pol
    info.pro = serie in ("A", "F") and tec == "QLED" or bool(re.search(r"\bPRO\b", T))
    info.tecnologia = tec
    info.codice = f"{serie}{' PRO' if info.pro else ''} {pol}"
    info.core = f"{pol}{serie}{'PRO' if info.pro else ''}"
    ris = trova_risoluzione(T) or ("HD" if pol <= 32 else "")
    info.chiave = serie + ("-HD" if ris in ("HD", "FHD") and serie in ("A", "F") and not info.pro else "")
    info.famiglia = f"XIAOMI-{tec}-{'S' if serie == 'S' else 'AF'}"
    info.regola = "caratteristiche"
    info.note.append("caratteristiche")
    return True


# ----------------------------------------------------------------- altre marche
def _generica(T: str, info: InfoTV):
    """Altre marche (TCL, Philips, Sony...): codice = primo token con pollici+lettere.
    Tecnologia, fascia e famiglia arrivano poi dal catalogo (applica_catalogo);
    altrimenti famiglia = marca + serie letterale (es. SHARP-GR8), senza la tecnologia del titolo."""
    m = re.search(r"\b(?:[A-Z]{1,4})?(\d{2,3})([A-Z]{1,4})(\d{1,4})([A-Z0-9]*)\b", T)
    tec_titolo = tecnologia_testo(T)
    info.pro = bool(re.search(r"\bPRO\b", T))
    info.regola = "GENERICA"
    if not m and info.marca == "SONY":
        b = re.search(r"BRAVIA\s?([2-9])\b", T)
        if b and not info.pollici:  # "SONY 65 BRAVIA 8": diagonale come numero isolato
            n = re.search(r"\b(3[2-9]|[4-9]\d|1[01]\d)\b", T)
            info.pollici = int(n.group(1)) if n else None
        if b and info.pollici:
            info.codice = f"BRAVIA {b.group(1)} {info.pollici}"
            info.core = f"{info.pollici}BRAVIA{b.group(1)}"
            info.chiave = f"BRAVIA {b.group(1)}"
            info.tecnologia = tec_titolo
            info.famiglia = f"SONY-BRAVIA{b.group(1)}"
            info.regola = "SONY-bravia"
            return True
    if not m:  # codici tipo TE43759S48U4P (Telefunken): lettere + pollici + cifre
        m2 = re.search(r"\b[A-Z]{1,3}(\d{2})\d{2,4}[A-Z][A-Z0-9]{2,}\b", T)
        if m2 and (not info.pollici or int(m2.group(1)) == info.pollici):
            info.codice = m2.group(0)
            info.pollici = info.pollici or int(m2.group(1))
            info.core = m2.group(0)
    if not m:
        info.tecnologia = tec_titolo
        info.famiglia = f"{info.marca}-"
        return bool(info.codice)
    info.codice = m.group(0)
    info.pollici = info.pollici or int(m.group(1))
    info.core = m.group(1) + m.group(2) + m.group(3)
    info.chiave = m.group(2) + m.group(3) + re.sub(r"\d.*", "", m.group(4))
    info.tecnologia = tec_titolo
    info.famiglia = f"{info.marca}-{m.group(2)}{m.group(3)[0]}"
    return True


def _voce_catalogo(info: InfoTV, T: str):
    """Serie del catalogo che corrisponde al modello: prefisso più lungo della chiave
    (es. chiave QN95 -> voce QN95 batte QN9), rispettando il flag PRO se la voce lo indica.
    Per le voci lunghe (BEOVISION, BRAVIA 8) basta che compaiano nel testo."""
    m = _CAT["marche"].get(info.marca)
    if not m:
        return None, None
    chiave = (info.chiave or "").replace(" ", "")
    migliore, punti = None, -1
    for v in m.get("serie", []):
        serie = _norm(v.get("serie", ""))
        if not serie:
            continue
        compatta = serie.replace(" ", "")
        if v.get("pro") is not None and bool(v["pro"]) != info.pro:
            continue
        p = -1
        if chiave and chiave.startswith(compatta):
            p = 100 + len(compatta) * 2 + (1 if v.get("pro") is not None else 0)
        elif (len(compatta) >= 4 or " " in serie) and re.search(rf"(?<![A-Z0-9]){re.escape(serie)}(?![A-Z0-9])", T):
            p = len(compatta)
        if p > punti:
            migliore, punti = v, p
    return m, migliore


def applica_catalogo(info: InfoTV, T: str):
    m, v = _voce_catalogo(info, T)
    if v:
        info.tecnologia = v.get("tecnologia") or info.tecnologia
        info.fascia = v.get("fascia") or info.fascia
        info.famiglia = f"{info.marca}-{v.get('famiglia') or (info.tecnologia + '-' + info.fascia)}"
        info.fascia_fonte = "catalogo"
        info.regola = f"catalogo: {m['marca']} {v['serie']}"
        if m.get("ignora_pro"):
            info.pro = False  # es. TCL "Q7D Pro": PRO è parte del nome, non una variante
        if not info.codice and info.pollici:  # nessun codice (es. Beovision): serie + pollici
            info.codice = f"{v['serie']} {info.pollici}"
            info.core = f"{info.pollici}{v['serie'].replace(' ', '')}"
        return True
    if m and not info.fascia and m.get("fascia_predefinita"):
        f = m["fascia_predefinita"]
        info.fascia = "BASE" if f == "ENTRY" and trova_risoluzione(T) in ("HD", "FHD") else f
        info.tecnologia = info.tecnologia or m.get("tecnologia_predefinita") or ""
        info.fascia_fonte = "marca"
    return False


# Fascia stimata dal prezzo (marche e serie sconosciute): soglie in €/pollice per un 55",
# scalate con la diagonale perché i TV grandi costano di più al pollice.
_SOGLIE_PREZZO = [("BASE", 7), ("ENTRY", 12), ("MID", 20), ("PREMIUM", 32)]


def stima_fascia(prezzo: float | None, pollici: int | None, tecnologia: str = "") -> str:
    if not prezzo or not pollici:
        return ""
    if prezzo < pollici * 2.5:  # 14 € per un 55": rata mensile, accessorio o prezzo letto male, non il TV
        return ""
    k = (pollici / 55) ** 0.6 * (1.4 if tecnologia == "OLED" else 1.0)
    al_pollice = prezzo / pollici
    for f, soglia in _SOGLIE_PREZZO:
        if al_pollice < soglia * k:
            return f
    return "TOP"


def leggi_prezzo(t: str) -> float | None:
    """Primo prezzo in € o £ del testo ("1.299,00 €", "€ 549", "£1,099.00"). Un anno seguito da € ("2025 € 399")
    non è un prezzo."""
    t = re.sub(r"\b20[1-3]\d\s?(?=[€£])", " ", t or "")  # "2025 € 399": l'anno non è il prezzo
    for m in re.finditer(r"(?<![\d.,])(\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?|\d+(?:\.\d{2})?)\s?[€£]|[€£]\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|\d+)", t or ""):
        x = (m.group(1) or m.group(2)).replace(" ", "")
        if re.fullmatch(r"20[1-3]\d", x):
            continue
        if re.search(r",\d{2}$", x):
            x = x.replace(".", "").replace(",", ".")
        elif re.search(r"\.\d{2}$", x):  # formato inglese 1,099.00
            x = x.replace(",", "")
        else:
            x = x.replace(",", "").replace(".", "") if re.search(r"[.,]\d{3}$", x) else x
        try:
            return float(x)
        except ValueError:
            continue
    return None


# fascia comune per le marche con regole proprie (LG, Hisense, Samsung): ricavata dalla famiglia
_FASCIA_FAMIGLIA = {"LG-UHD-PREMIUM": "MID", "LG-MINILED-ENTRY": "MID", "HISENSE-QLED-HD": "BASE",
                    "HISENSE-LED-HD": "BASE", "HISENSE-MINILED-ENTRY": "MID", "HISENSE-MINILED-MID": "PREMIUM",
                    "HISENSE-MINILED-PREMIUM": "TOP"}
LIVELLI = {"BASE": 0, "ENTRY": 1, "MID": 2, "PREMIUM": 3, "TOP": 4}


def fascia_da_famiglia(fam: str) -> str:
    if not fam:
        return ""
    if fam in _FASCIA_FAMIGLIA:
        return _FASCIA_FAMIGLIA[fam]
    if "8K" in fam or "SUPERPREMIUM" in fam:
        return "TOP"
    for tok in ("PREMIUM", "MID", "ENTRY"):  # SUPERENTRY contiene ENTRY
        if tok in fam:
            return tok
    return ""


_ACCESSORIO = re.compile(
    r"TELECOMANDO|FERNBEDIENUNG|T[EÉ]L[EÉ]COMMANDE|MANDO A DISTANCIA|REMOTE CONTROL|STAFFA|SUPPORTO A PARETE|"
    r"WANDHALTERUNG|HALTERUNG|SUPPORT MURAL|SOPORTE DE PARED|WALL MOUNT|BRACKET|\bBEZEL\b|"
    r"FRIGORIFERO|K[UÜ]HLSCHRANK|R[EÉ]FRIG[EÉ]RATEUR|FRIGOR[IÍ]FICO|FRIDGE|"
    r"LAVATRICE|WASCHMASCHINE|LAVE-LINGE|LAVADORA|WASHING MACHINE|ERSATZ|RICAMBIO|REPLACEMENT|PIÈCE DE RECHANGE|"
    r"\bPEZZI\b|\bPCS\b|\bST[UÜ]CK\b|\bPI[EÈ]CES\b|LIGHTSTRIP|HUE PLAY|RUBAN LED|LED STRIP|STRIP LED|STRISCIA LED|STRISCE LED|LED-STREIFEN|BACKLIGHT|RETROILLUMINAZIONE|R[EÉ]TRO[EÉ]CLAIRAGE|TIRA DE LED|SCHUTZFOLIE|PELLICOLA|"
    r"PROIETTORE|BEAMER|PROJECTOR|VID[EÉ]OPROJECTEUR|PROYECTOR|ST[AÄ]NDER|TV-BEINE|\bBEINE\b|PIEDINI|PIEDS TV|PATAS|"
    r"T-?CON\b|SCHEDA LOGICA|LOGIC BOARD|MAINBOARD|SCHEDA MADRE|ALIMENTATORE|NETZTEIL|POWER SUPPLY|CARICATORE|CHARGER|"
    r"MULTIPRESA|FILM PROTECTEUR|PROTECTOR DE PANTALLA|SCREEN PROTECTOR|DISPLAYSCHUTZ|BEFESTIGUNGS|CLIPS?\b|"
    r"SUPPORT TV|SUPPORTO TV|SOPORTE TV|TV MOUNT|TV STAND|MEUBLE TV|MOBILE TV|TV-SCHRANK|TV-BOARD|LOWBOARD")
_ACC_DEBOLE = re.compile(r"CORNICE|\bRAHMEN\b|\bMONITOR\b|\bCAVO\b|\bKABEL\b|\bC[AÂ]BLE\b")  # solo se non è un TV
_ACC_URL = re.compile(r"/(accessori|zubehoer|zubehor|accessoires|accesorios|accessories|elettrodomestici|haushalt|"
                      r"electromenager|electrodomesticos)[/-]", re.I)


def e_accessorio(testo: str, url: str = "") -> bool:
    """Accessori e altri prodotti che le ricerche dei negozi mescolano ai TV (telecomandi, staffe, cornici, frigoriferi...)."""
    T = _norm(testo)
    if _ACC_URL.search(url or ""):
        return True
    if re.search(r"SOUNDBAR|SOUND BAR|BARRA DE SONIDO|BARRE DE SON", T) and not re.search(r"BUNDLE|\+ ?TV|TV ?\+", T):
        return True
    if _ACCESSORIO.search(T):
        return True
    return bool(_ACC_DEBOLE.search(T)) and not re.search(r"SMART ?TV|\bTV (LED|QLED|OLED)|FERNSEHER|T[EÉ]L[EÉ]VISEUR|TELEVISOR", T)


def _unisci_codici(T: str) -> str:
    """Codici scritti a pezzi (MediaMarkt/Saturn): "LG 50 QNED 82 A 6 BAEU" -> 50QNED82A6BAEU, "OLED 55 C 5 ELB" -> OLED55C5ELB."""
    T = re.sub(r"\b(\d{2,3}) (QNED|NANO|UA|UT|UR|UQ|QN|Q|U) ?(\d{1,3}) ?([A-Z]) ?(\d) ?([A-Z]{2,4})\b",
               lambda m: "".join(m.groups()), T)
    T = re.sub(r"\bOLED ?(\d{2,3}) ?([A-Z]) ?(\d) ?([A-Z]{2,4})\b", lambda m: "OLED" + "".join(m.groups()), T)
    return T


def analizza(testo: str, codice_noto: str = "", marca_nota: str = "", prezzo: float | None = None) -> InfoTV:
    """Analizza titolo prodotto (+ eventuale codice modello già noto, marca e prezzo letti da Amazon)."""
    if not _CAT["marche"]:
        imposta_catalogo(catalogo_predefinito())
    T = _unisci_codici(_norm(f"{codice_noto} {testo}"))
    info = InfoTV(testo=testo or "")
    info.marca = trova_marca(T) or marca_da_codice(codice_noto or T)
    if not info.marca and marca_nota:
        info.marca = trova_marca(marca_nota) or _norm(marca_nota)
        info.marca_nuova = info.marca not in _CAT["marche"]
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
    elif info.marca == "XIAOMI":
        ok = _xiaomi(T, info)
    elif info.marca == "METZ":
        _metz(T, info)  # solo codice e anno; tecnologia e fascia dal catalogo/caratteristiche
    if not ok:
        _generica(T, info)
    applica_catalogo(info, T)
    mz = info.marca == "METZ" and re.search(r"\b\d{2,3}M([A-Z])[A-Z](\d{4})", info.codice or "")
    if mz:  # Metz: 7000, 7030, 7500, 8001 sono modelli diversi anche nella stessa tecnologia
        info.famiglia = f"METZ-M{mz.group(1)}{mz.group(2)}"
    if pollici_testo and info.pollici != pollici_testo:
        info.note.append(f"pollici codice {info.pollici} ≠ titolo {pollici_testo}")
        info.pollici = pollici_testo
    if info.anno is None:
        info.anno = anno_t
    t_tit = tecnologia_testo(T)
    if not info.tecnologia:
        info.tecnologia = t_tit
    elif _RANGO_TEC.get(t_tit, 0) > _RANGO_TEC.get(info.tecnologia, 0) and info.tecnologia != "OLED" and t_tit != "OLED":
        # il titolo dichiara una tecnologia superiore a quella del catalogo (es. "QLED" su una serie registrata LED)
        info.note.append(f"tecnologia dal titolo {t_tit} (catalogo {info.tecnologia})")
        info.tecnologia = t_tit
    if info.risoluzione == "HD" and info.pollici and info.pollici >= 43 and not re.search(r"HD[\s-]?READY|720P|1366", T):
        info.risoluzione = ""  # "HD Smart TV" su un 55": quasi sempre è un 4K, lo dirà la scheda
    if not info.fascia and info.famiglia:
        info.fascia = fascia_da_famiglia(info.famiglia)
        info.fascia_fonte = "regole" if info.fascia else ""
    if not info.fascia and prezzo:
        info.fascia = stima_fascia(prezzo, info.pollici, info.tecnologia)
        info.fascia_fonte = "stimata"
    if not info.fascia and info.tecnologia == "LED" and info.risoluzione:
        # serie sconosciuta e nessun prezzo: un LED Full HD/HD è per forza di fascia base, un LED 4K al più entry
        info.fascia = "BASE" if info.risoluzione in ("HD", "FHD") else "ENTRY" if info.risoluzione == "4K" else ""
        info.fascia_fonte = "presunta" if info.fascia else ""
    if not info.codice and info.marca and info.pollici and info.tecnologia and info.fascia:
        # nessun codice leggibile, ma le caratteristiche bastano: modello "per caratteristiche"
        info.codice = f"{info.marca.title()} {info.pollici}\" {info.tecnologia}"
        info.core = f"CAR-{info.pollici}-{info.tecnologia}-{len(info.testo)}"
        info.regola = "caratteristiche"
        info.note.append("caratteristiche")
        info.famiglia = info.famiglia if info.famiglia and not info.famiglia.endswith("-") else f"{info.marca}-{info.tecnologia}-{info.fascia}"
    if not info.risoluzione and info.pollici and info.pollici <= 32:
        info.risoluzione = "HD"  # sotto i 32" non esistono TV 4K: titolo senza risoluzione = HD/Full HD
    if not info.risoluzione and (info.tecnologia == "OLED" or info.pollici and info.pollici >= 50):
        info.risoluzione = "4K"  # sopra i 50" (e negli OLED) il Full HD non si vende più: titolo muto = 4K
    info.dolby_vision = "DOLBY VISION" in T
    info.hdr10plus = bool(re.search(r"HDR\s?10\s?\+|HDR10 PLUS", T))
    info.hdmi21 = bool(re.search(r"HDMI\s?2\.1", T))
    return info


# ----------------------------------------------------------------- scheda tecnica dell'inserzione
# Voci (in IT/DE/FR/ES/EN) delle schede tecniche di Amazon e dei negozi.
_VOCI = {
    "anno": ["anno del modello", "anno modello", "anno di uscita", "anno di lancio", "anno di produzione", "modelljahr",
             "erscheinungsjahr", "jahr", "année du modèle", "année de sortie", "model year", "release year",
             "año del modelo", "año de lanzamiento", "ld:data"],
    "pollici": ["diagonale schermo", "diagonale dello schermo", "diagonale", "dimensione schermo", "dimensioni schermo",
                "bildschirmdiagonale", "bildschirmgröße", "bilddiagonale", "screen size", "display size",
                "taille de l'écran", "taille d'écran", "diagonale de l'écran", "tamaño de pantalla", "tamaño de la pantalla"],
    "risoluzione": ["risoluzione", "risoluzione schermo", "risoluzione dello schermo", "auflösung", "bildschirmauflösung",
                    "resolution", "display resolution", "résolution", "resolución", "resolución de pantalla"],
    "tecnologia": ["tecnologia display", "tecnologia dello schermo", "tecnologia schermo", "tipo di display", "tipo display",
                   "tipo di schermo", "display-technologie", "displaytechnologie", "bildschirmtechnologie", "displaytyp",
                   "display type", "display technology", "panel type", "technologie d'affichage", "type d'écran",
                   "tecnología de pantalla", "tipo de pantalla"],
    "hz": ["frequenza di aggiornamento", "frequenza di aggiornamento dello schermo", "bildwiederholrate",
           "bildwiederholfrequenz", "refresh rate", "taux de rafraîchissement", "fréquence de rafraîchissement",
           "frecuencia de actualización", "tasa de refresco"],
    "marca": ["marca", "marchio", "marke", "hersteller", "brand", "marque", "ld:marca"],
    "modello": ["numero modello articolo", "numero modello", "modellnummer", "herstellernummer", "model number",
                "item model number", "référence du modèle", "numéro du modèle", "número de modelo", "ld:modello", "ld:mpn"],
}
_TAGLIE = [24, 32, 40, 42, 43, 48, 50, 55, 58, 65, 70, 75, 77, 83, 85, 98, 100, 115]


def _voce(scheda: dict, tipo: str):
    for nome in _VOCI[tipo]:
        if nome in scheda:
            return scheda[nome]
    for k, v in scheda.items():  # voce che inizia con il nome cercato (es. "auflösung (pixel)")
        if any(k.startswith(n) for n in _VOCI[tipo] if len(n) > 4):
            return v
    return None


def leggi_scheda(scheda: dict | None) -> dict:
    """Dalla scheda tecnica (voce -> valore) ricava anno, pollici, risoluzione, tecnologia, frequenza, marca, modello."""
    out = {}
    if not scheda:
        return out
    v = _voce(scheda, "anno")
    if v:
        m = re.search(r"\b(20[1-3]\d)\b", v)
        if m:
            out["anno"] = int(m.group(1))
    v = _voce(scheda, "pollici")
    if v:
        V = _norm(v).replace(",", ".")
        m = re.search(r"(\d{2,3}(?:\.\d)?)\s*(?:\"|''|ZOLL|POLLICI|INCH|POUCES|PULGADAS)", V)
        if m:
            pol = float(m.group(1))
            out["pollici"] = min(_TAGLIE, key=lambda t: (abs(t - pol), -t)) if abs(pol - round(pol)) > 0.2 else round(pol)
        else:
            m = re.search(r"(\d{2,3}(?:\.\d)?)\s*CM", V)
            if m:  # cm -> pollici, arrotondato alla taglia commerciale più vicina
                pol = float(m.group(1)) / 2.54
                out["pollici"] = min(_TAGLIE, key=lambda t: (abs(t - pol), -t))  # 108 cm = 42,5": vale 43
    v = _voce(scheda, "risoluzione")
    if v:
        V = _norm(v)
        r = ("8K" if re.search(r"7680|8K", V) else "4K" if re.search(r"3840|4K|UHD|ULTRA[\s-]?HD|2160", V)
             else "FHD" if re.search(r"1920|FULL[\s-]?HD|FHD|1080", V) else "HD" if re.search(r"1366|1280|HD|720", V) else "")
        if r:
            out["risoluzione"] = r
    # tecnologia: la voce generica ("LED") e quelle sulla retroilluminazione ("Mini LED"): vale la più precisa
    cand = [tecnologia_testo(v) for v in [_voce(scheda, "tecnologia")] + [
        v for k, v in scheda.items() if re.search(r"retroillumin|backlight|hintergrundbeleucht|rétroéclairage|retroilumin|"
                                                  r"tipo di pannello|panel type|paneltyp|type de dalle|tipo de panel", k)] if v]
    cand = [c for c in cand if c]
    if cand:
        out["tecnologia"] = max(cand, key=lambda c: _RANGO_TEC.get(c, 0))
    # frequenza: la voce della scheda, ma se altrove la scheda dice esplicitamente la nativa ("60Hz with 120Hz
    # Game Boost") vale quella; valori oltre 165 Hz sono sempre marketing (es. "288 Hz")
    voci_hz = [scheda.get(n) for n in _VOCI["hz"] if scheda.get(n)] + \
        [v for k, v in scheda.items() if isinstance(v, str) and re.search(r"(hertz|hercios|hz)$", k)]
    vals = [trova_hz(v if re.search(r"HZ", v, re.I) else f"{v} Hz") for v in voci_hz]
    vals = [x for x in vals if x and x <= 165]
    altro = " | ".join(str(v) for k, v in scheda.items() if isinstance(v, str) and v not in voci_hz)
    nativa = trova_hz(altro) if re.search(r"\d\s?HZ\s+(WITH|CON|MIT|AVEC)\b", _norm(altro)) else None
    if nativa or vals:
        out["hz"] = nativa or min(vals)
    for k in ("marca", "modello"):
        v = _voce(scheda, k)
        if v:
            out[k] = v.strip()
    tutto = _norm(" ".join(f"{k} {v}" for k, v in scheda.items()))
    out["dolby_vision"] = "DOLBY VISION" in tutto
    out["hdr10plus"] = bool(re.search(r"HDR\s?10\s?\+|HDR10 PLUS", tutto))
    out["hdmi21"] = bool(re.search(r"HDMI\s?2\.1", tutto))
    return out


def arricchisci(info: InfoTV, dati: dict) -> InfoTV:
    """I dati della scheda tecnica prevalgono su quelli dedotti dal titolo (risoluzione, frequenza; l'anno solo se il
    titolo non lo dice: nelle schede è spesso sbagliato);
    pollici e tecnologia la integrano solo se mancano (la tecnologia del Catalogo resta la più stabile)."""
    if not dati:
        return info
    for k in ("risoluzione", "hz"):
        if dati.get(k):
            setattr(info, k, dati[k])
    if dati.get("anno") and not trova_anno_testo(_norm(info.testo)):  # l'anno nel titolo vale più della scheda
        info.anno = dati["anno"]
    if dati.get("pollici") and not info.pollici:
        info.pollici = dati["pollici"]
    if dati.get("tecnologia") and not info.tecnologia:
        info.tecnologia = dati["tecnologia"]
    for k in ("dolby_vision", "hdr10plus", "hdmi21"):
        if dati.get(k):
            setattr(info, k, True)
    return info


# ----------------------------------------------------------------- parametri
PARAMETRI_DEFAULT = {
    "modalita": "stessa_marca",   # "stessa_marca" = alternativa della stessa marca, "concorrente" = altra marca equivalente
    "pollici": {"attivo": True, "tolleranza": 0},
    "famiglia": {"attivo": True},
    "tecnologia": {"attivo": True, "equivalenze": [["MINILED", "NEOQLED"]]},
    "risoluzione": {"attivo": True},
    "refresh": {"attivo": True},
    # ricerca "simile" (regole di somiglianza) oppure "identico" (lo stesso modello dell'ASIN, anche con varianti di codice)
    "ricerca": "simile",
    # modo "asin": stesso anno del TV Amazon (se non si ricava, vale "valore"); modo "fisso": sempre "valore"
    "anno": {"attivo": True, "modo": "asin", "valore": __import__("datetime").date.today().year, "accetta_ignoto": True},
    "pro": {"attivo": True},
    "dolby_vision": {"attivo": False},
    "hdr10plus": {"attivo": False},
    "hdmi21": {"attivo": False},
    "max_match": 1,
    "verifica_url": True,
    "ponte_idealo": True,   # se il sito del retailer non è leggibile, cerca le sue offerte su idealo
}


def unisci_parametri(p: dict | None) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PARAMETRI_DEFAULT.items()}
    p = dict(p or {})
    # compatibilità con le ricerche salvate prima della modalità: "stessa marca" spenta = concorrenti
    if "modalita" not in p and isinstance(p.get("stessa_marca"), dict):
        p["modalita"] = "stessa_marca" if p["stessa_marca"].get("attivo", True) else "concorrente"
    p.pop("stessa_marca", None)
    for k, v in p.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    if out["modalita"] not in ("stessa_marca", "concorrente"):
        out["modalita"] = "stessa_marca"
    return out


def _tec_equivalenti(a: str, b: str, gruppi) -> bool:
    if a == b:
        return True
    return any(a in g and b in g for g in (gruppi or []))


def anno_obiettivo(P: dict, amz: InfoTV) -> int:
    """Anno richiesto ai modelli trovati: quello del TV Amazon (predefinito) oppure un anno fisso scelto sul sito."""
    a = P.get("anno") or {}
    if a.get("modo", "asin") == "asin" and amz is not None and amz.anno:
        return int(amz.anno)
    return int(a.get("valore") or __import__("datetime").date.today().year)


def confronta_param(amz: InfoTV, cand: InfoTV, P: dict):
    """Ogni criterio si accende/spegne da P (vedi PARAMETRI_DEFAULT).
    Si confrontano prima le caratteristiche (diagonale, tecnologia, risoluzione, frequenza, anno), poi la fascia.
    Modalità "stessa_marca": stessa marca, stessa fascia, codice diverso (la stessa famiglia è preferita).
    Modalità "concorrente": altra marca, stessa tecnologia e fascia (±1 ammessa, penalizzata).
    Ritorna (ok, motivo, punteggio): punteggio più basso = più vicino."""
    concorrente = P.get("modalita") == "concorrente"
    if not cand.codice:
        return False, "codice modello non leggibile", 0
    car = "caratteristiche" in cand.note
    if not cand.marca:
        return False, "marca non riconosciuta", 0
    if concorrente and cand.marca == amz.marca:
        return False, "stessa marca (cerco concorrenti)", 0
    if not concorrente:
        if cand.marca != amz.marca:
            return False, "marca diversa", 0
        if stesso_modello(amz, cand):
            return False, "stesso modello (escluso)", 0
    note, score = [], 0
    if P["pollici"]["attivo"]:
        tol = int(P["pollici"].get("tolleranza") or 0)
        if cand.pollici is None or amz.pollici is None or abs(cand.pollici - amz.pollici) > tol:
            return False, f"pollici {cand.pollici}", 0
    score += 100 * abs((cand.pollici or 0) - (amz.pollici or 0))
    if P["tecnologia"]["attivo"] and amz.tecnologia:
        if not cand.tecnologia:
            if concorrente:
                return False, "tecnologia non determinabile", 0
            note.append("tecnologia da verificare")
            score += 30
        elif not _tec_equivalenti(amz.tecnologia, cand.tecnologia, P["tecnologia"].get("equivalenze")):
            return False, f"tecnologia {cand.tecnologia}", 0
    if P["pro"]["attivo"] and not concorrente and cand.pro != amz.pro:
        return False, "PRO vs non-PRO", 0
    if P["risoluzione"]["attivo"] and amz.risoluzione and cand.risoluzione \
            and amz.risoluzione != cand.risoluzione:
        if not (concorrente and {amz.risoluzione, cand.risoluzione} <= {"HD", "FHD"}):
            return False, f"risoluzione {cand.risoluzione}", 0
        note.append(f"risoluzione {cand.risoluzione}")
        score += 10
    if P["refresh"]["attivo"] and hz_diverse(amz.hz, cand.hz):
        return False, f"refresh {cand.hz}Hz", 0
    # Dolby Vision / HDR10+ / HDMI 2.1 si controllano sulla pagina prodotto (nucleo.elabora_asin)
    if P["anno"]["attivo"]:
        target = anno_obiettivo(P, amz)
        if cand.anno is not None and cand.anno != target:
            return False, f"anno {cand.anno}", 0
        if cand.anno is None:
            if not P["anno"].get("accetta_ignoto", True) and not P.get("verifica_url", True):
                return False, "anno non determinabile", 0
            note.append("anno da verificare")
            score += 5
    # fascia/famiglia per ultima: le caratteristiche (diagonale, tecnologia, risoluzione, frequenza, anno)
    # decidono prima; la serie serve solo a preferire l'alternativa più vicina
    if P["famiglia"]["attivo"]:
        if not concorrente:
            # stessa famiglia = alternativa ideale; famiglia diversa ma stessa fascia = simile, segnalato.
            # Così una piccola differenza di classificazione non fa perdere un modello ovviamente simile.
            if cand.famiglia and cand.famiglia == amz.famiglia:
                pass
            elif amz.fascia_fonte in ("catalogo", "regole"):
                # serie censita (catalogo o regole di marca): un'altra serie non è un modello simile
                return False, f"altra serie ({cand.famiglia.split('-', 1)[-1] or '?'}, ASIN {amz.famiglia.split('-', 1)[-1]})", 0
            elif amz.fascia and cand.fascia == amz.fascia:
                note.append(f"altra serie, stessa fascia {cand.fascia.lower()}")
                score += 30
            elif amz.fascia and cand.fascia:
                return False, f"fascia {cand.fascia.lower()} (ASIN {amz.fascia.lower()})", 0
            else:
                return False, f"serie diversa e fascia non determinabile ({cand.famiglia or '?'})", 0
        elif amz.fascia:
            if not cand.fascia:
                return False, "fascia non determinabile", 0
            else:
                d = abs(LIVELLI[cand.fascia] - LIVELLI[amz.fascia])
                if d > 1:
                    return False, f"fascia {cand.fascia.lower()}", 0
                score += 50 * d
                if d:
                    note.append(f"fascia {cand.fascia.lower()} (ASIN {amz.fascia.lower()})")
    if not concorrente:  # vicinanza tra i numeri di serie della stessa marca
        na = re.findall(r"\d+", amz.core[len(str(amz.pollici or "")):]) or ["0"]
        nb = re.findall(r"\d+", cand.core[len(str(cand.pollici or "")):]) or ["0"]
        score += abs(int(na[0]) - int(nb[0]))
    if car:
        note.insert(0, "riconosciuto dalle caratteristiche")
        score += 20
    return True, ", ".join(note) or "ok", score


# ----------------------------------------------------------------- matching
def stesso_modello(a: InfoTV, b: InfoTV) -> bool:
    if not a.core or not b.core:
        return False
    x, y = a.core, b.core
    return x == y or x in b.codice or y in a.codice


def _cod_norm(c: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())


def stesso_modello_esatto(a: InfoTV, b: InfoTV) -> bool:
    """Modalità "Stesso modello": codice modello IDENTICO a quello Amazon (maiuscole, spazi e trattini a parte):
    QE55Q7FAAUXZT ≠ QE55Q7FAATXZT, 50E7DS PRO ≠ 50E7DS. Diagonale uguale.
    Unica eccezione Xiaomi, che non scrive codici nei titoli: vale il nome (TV F Pro 43 = L43MB-FPEU).
    L'anno NON conta: lo stesso modello è spesso venduto con anni diversi nel titolo (il risultato lo segnala)."""
    if not a.codice or not b.codice or not a.marca or a.marca != b.marca:
        return False
    if "caratteristiche" in a.note or "caratteristiche" in b.note:
        return False  # "Metz 32\" QLED" non è un codice modello
    if a.pollici and b.pollici and a.pollici != b.pollici:
        return False
    if a.pro != b.pro:
        return False
    if a.marca == "XIAOMI" and a.core and b.core:
        return a.core == b.core
    return _cod_norm(a.codice) == _cod_norm(b.codice)


def confronta_identico(amz: InfoTV, cand: InfoTV, P: dict | None = None):
    """Come confronta_param, ma per la modalità "Stesso modello"."""
    if not cand.codice:
        return False, "codice modello non leggibile", 0
    if cand.marca != amz.marca:
        return False, "marca diversa", 0
    if stesso_modello_esatto(amz, cand):
        return True, "ok", 0
    return False, f"modello diverso ({cand.codice})", 0


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
    if hz_diverse(amz.hz, cand.hz):
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
