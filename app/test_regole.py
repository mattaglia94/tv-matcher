"""Test delle regole di riconoscimento e somiglianza, con titoli reali visti su Amazon e sui retailer.
Uso: python app/test_regole.py   (esce con errore se un caso non torna)
Ogni volta che un risultato sbagliato viene segnalato, il caso va aggiunto qui."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regole import analizza, confronta_param, unisci_parametri  # noqa: E402

# titolo -> (marca, tecnologia, fascia)
RICONOSCIMENTO = [
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED,Smart TV,Fire TV", ("XIAOMI", "QLED", "MID")),
    ("XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, Smart TV, Fire TV, HD", ("XIAOMI", "QLED", "MID")),
    ("XIAOMI TV F 32 2025, 32 pollici (81 cm), HD, Smart TV, Fire TV", ("XIAOMI", "LED", "BASE")),
    ("Xiaomi TV 43 pollici 2026, HD Smart TV Fire TV Dolby Audio L43MB-FAVEU", ("XIAOMI", "LED", "BASE")),
    ("XIAOMI TV F 65 2025, 65 pollici (165 cm),4K UHD,Smart TV, Fire TV", ("XIAOMI", "LED", "ENTRY")),
    ("xiaomi tv a pro 32 2026 tv nero", ("XIAOMI", "QLED", "MID")),
    ("Xiaomi TV A 32 TV LED piatto 32 HD", ("XIAOMI", "LED", "BASE")),
    ("XIAOMI A 32 EU TV LED, SMART TV, 32 \", LCD, HD, Processore Cortex-A55, Black, Classe E", ("XIAOMI", "LED", "BASE")),
    ("Xiaomi 50APRO2 TV 127 cm (50\") 4K Ultra HD Smart TV Wi-Fi Grigio", ("XIAOMI", "QLED", "MID")),
    # codici Xiaomi ufficiali (Amazon.de, Otto)
    ("Xiaomi TV F 65 Zoll 2025, 4K UHD, Smart TV, Fire OS8, HDR10, L65MB-FAEU", ("XIAOMI", "LED", "ENTRY")),
    ("Xiaomi L65MB-APEU 165 cm (65 Zoll) 4K Ultra HD Smart TV Google TV", ("XIAOMI", "QLED", "MID")),
    ("Xiaomi L65MB-SEU 165 cm (65 Zoll) 4K Ultra HD Smart TV Google TV", ("XIAOMI", "MINILED", "PREMIUM")),
    ("Xiaomi L32MB-FPEU LED-Fernseher 80 cm (32 Zoll) HD Smart TV", ("XIAOMI", "QLED", "MID")),
    ("TCL 75C6K QD-Mini LED 4K 144Hz 2025", ("TCL", "MINILED", "ENTRY")),
    ("TCL 65C7L SQD Mini LED", ("TCL", "MINILED", "MID")),
    ("TCL 55C655 QLED", ("TCL", "QLED", "ENTRY")),
    ("TCL 75T6C QLED 4K 2026", ("TCL", "QLED", "ENTRY")),
    ("TCL 43S5L Smart TV QLED FHD 43", ("TCL", "LED", "BASE")),
    ("Hisense 75E7Q 4K QLED 2025", ("HISENSE", "QLED", "ENTRY")),
    ("Hisense 65E7NQ PRO", ("HISENSE", "QLED", "MID")),
    ("Hisense 65U7Q PRO Mini LED", ("HISENSE", "MINILED", "PREMIUM")),
    ("Hisense 75UR9S RGB Mini LED", ("HISENSE", "MINILED", "TOP")),
    ("Hisense 43A4N HD", ("HISENSE", "LED", "BASE")),
    ("HISENSE 75Q7S PRO, Smart TV QLED 144Hz 75\" 4K", ("HISENSE", "QLED", "ENTRY")),
    ("Samsung QE75Q7FAATXZT QLED 4K 2025", ("SAMSUNG", "QLED", "ENTRY")),
    ("Samsung QE65QN90FATXZT Neo QLED", ("SAMSUNG", "NEOQLED", "PREMIUM")),
    ("Samsung QE65S90F OLED", ("SAMSUNG", "OLED", "PREMIUM")),
    ("Samsung QE43LS03H The Frame", ("SAMSUNG", "QLED", "MID")),
    ("Samsung UE50U8000F Crystal UHD", ("SAMSUNG", "LED", "ENTRY")),
    ("LG OLED55C54LA 2025", ("LG", "OLED", "PREMIUM")),
    ("LG OLED65B66LA", ("LG", "OLED", "MID")),
    ("LG 55QNED86A6A", ("LG", "MINILED", "ENTRY")),
    ("LG 65NU800B6LA 4K", ("LG", "LED", "MID")),
    ("LG 55UA73006LA", ("LG", "LED", "ENTRY")),
    ("Philips 55PUS8500/12 Ambilight 4K", ("PHILIPS", "LED", "MID")),
    ("Philips 55OLED810/12", ("PHILIPS", "OLED", "PREMIUM")),
    ("Sony KD-75X80L", ("SONY", "LED", "ENTRY")),
    ("Sony 65 Bravia 8 A OLED 4K", ("SONY", "OLED", "PREMIUM")),
    ("Panasonic TV-55W90A 4K", ("PANASONIC", "LED", "MID")),
    ("Telefunken Smart TV LED 4K 43\" TE43759S48U4P", ("TELEFUNKEN", "LED", "ENTRY")),
    ("Bang & Olufsen Beovision Contour 55\" OLED", ("BANG & OLUFSEN", "OLED", "TOP")),
]

# (titolo ASIN, titolo candidato, modalità, deve essere simile?)
SOMIGLIANZA = [
    # stessa marca
    ("XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, Smart TV, Fire TV, HD",
     "A-Pro-32-2026 XIA32APRO2 Xiaomi", "stessa_marca", True),
    ("XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, Smart TV, Fire TV, HD",
     "Xiaomi TV A 32 TV LED piatto 32 HD", "stessa_marca", False),       # non PRO, LED
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED", "Xiaomi TV A Pro 75 2026 QLED 4K", "stessa_marca", True),
    ("XIAOMI TV F 32 2025, 32 pollici (81 cm), HD, Smart TV, Fire TV", "Xiaomi TV A 32 2026", "stessa_marca", True),
    ("XIAOMI TV F 50, 50 pollici (127 cm), 4K UHD, Smart TV, Fire TV", "Xiaomi TV A 50 2026 4K", "stessa_marca", True),
    ("XIAOMI TV F 50, 50 pollici (127 cm), 4K UHD, Smart TV, Fire TV", "Xiaomi 50APRO2 TV 127 cm (50\") 4K Ultra HD", "stessa_marca", False),
    ("XIAOMI TV F Pro 50 2025, 50 pollici, 4K UHD QLED", "Xiaomi 50APRO2 TV 127 cm (50\") 4K Ultra HD", "stessa_marca", True),
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED", "XIAOMI TV F Pro 75 QLED", "stessa_marca", False),  # stesso modello
    ("Hisense 55E7Q 4K QLED 2026", "Hisense 55A7Q QLED 4K 2026", "stessa_marca", True),
    ("Xiaomi TV F 65 Zoll 2026, 4K UHD, Smart TV, Fire OS8, L65MC-FAEU", "Xiaomi L65MC-AUEU 165 cm (65 Zoll) 4K Ultra HD", "stessa_marca", True),
    ("Xiaomi TV F 65 Zoll 2025, 4K UHD, Smart TV, Fire OS8, L65MB-FAEU", "Xiaomi L65MB-SEU 165 cm (65 Zoll) 4K Mini LED", "stessa_marca", False),
    ("Hisense 55E7Q 4K QLED 2026", "Hisense 55U7Q Mini LED 2026", "stessa_marca", False),  # altra tecnologia
    ("Samsung QE65QN90HATXZT Neo QLED 2026", "Samsung QE65QN92HATXZT Neo QLED 2026", "stessa_marca", True),
    ("LG OLED55C64LA 2026", "LG OLED55C65LA 2026", "stessa_marca", True),
    ("LG OLED55C64LA 2026", "LG OLED55B66LA 2026", "stessa_marca", False),  # fascia diversa
    ("TCL 65C7L SQD Mini LED 2026", "TCL 65C8L SQD Mini LED 2026", "stessa_marca", False),
    # concorrente
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED", "TCL 75T8C QLED 4K 2026", "concorrente", True),
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED", "Hisense 75E7Q QLED 4K 2026", "concorrente", True),  # fascia vicina
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED", "TCL 75C6K QD-Mini LED 2026", "concorrente", False),
    ("Xiaomi TV 43 pollici 2026, HD Smart TV Fire TV L43MB-FAVEU", "TCL 43S5400 HD LED Smart TV 2026", "concorrente", True),
    ("Xiaomi TV 43 pollici 2026, HD Smart TV Fire TV L43MB-FAVEU", "LG 43QNED70B6C MiniLED 4K 2026", "concorrente", False),
    ("Bang & Olufsen Beovision Contour 65\" OLED 2026", "LG OLED65G66LS OLED evo G6 65 2026", "concorrente", True),
    ("Bang & Olufsen Beovision Contour 65\" OLED 2026", "TCL 65C7L Mini LED 2026", "concorrente", False),
    ("Samsung QE65S90H OLED 2026", "LG OLED65C64LA 2026", "concorrente", True),
    ("Samsung QE65S90H OLED 2026", "Samsung QE65S85H OLED 2026", "concorrente", False),  # stessa marca
]


class _BrowserFinto:
    """Simula Amazon, una pagina di ricerca e una pagina prodotto 'sporca' (menu con 8K, copyright 2025)."""
    def __init__(self, titolo, risultati, titolo_pagina, scheda=None, scheda_amazon=None):
        self.t, self.ris, self.tp, self.sch, self.sch_a = titolo, risultati, titolo_pagina, scheda or {}, scheda_amazon or {}

    def amazon(self, asin, dominio):
        return {"titolo": self.t, "modello": "", "img": "", "marca": "", "prezzo": "", "errore": "", "scheda": self.sch_a}

    def cerca(self, url, q):
        return url, [{"url": t[1], "testo": t[0]} if isinstance(t, tuple) else {"url": f"https://negozio.it/p{i}", "testo": t}
                     for i, t in enumerate(self.ris)], "ok"

    def verifica(self, url):
        if self.sch.get("_stato"):  # pagina bloccata dal sito
            return False, "", "", "", {"_stato": self.sch["_stato"]}
        corpo = "Menu: TV 8K OLED, offerte 2025, Classe energetica 2025 © 2025 negozio"
        return True, self.tp, corpo, "", self.sch

    def idealo_cerca(self, dominio, q):
        return [{"url": "https://www.idealo.de/preisvergleich/OffersOfProduct/206295504_-a-pro-75-2026-xiaomi.html",
                 "testo": t} for t in self.sch_a.get("_idealo", [])]


PAGINE = [  # (titolo ASIN, risultati di ricerca, titolo pagina prodotto, modalità, modello atteso)
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED", ["Xiaomi A Pro 75 2026 ELA5840EU TV QLED 75 UHD 4K"],
     "Xiaomi A Pro 75 2026 ELA5840EU TV QLED piatto 75\" UHD 4K", "stessa_marca", "A PRO 75"),
    ("XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, Smart TV, Fire TV, HD", ["Xiaomi TV A Pro 32 2026 TV nero"],
     "Xiaomi - TV A PRO 32 2026 TV, Nero", "stessa_marca", "A PRO 32"),
    # codice solo nell'indirizzo (Unieuro): pidXIA50APRO2 = Xiaomi A Pro 50
    ("Xiaomi TV F Pro 50 2025, 50 pollici, 4K UHD QLED", [("Smart TV 50 pollici 2026", "https://www.unieuro.it/online/TV-Led/ELA6088EU-pidXIA50APRO2")],
     "Xiaomi TV A Pro 50 2026 QLED 4K", "stessa_marca", "A PRO 50"),
    ("Samsung QE75QN80HATXZT Neo QLED 2026", [("Neo QLED 75 Vision AI 2026", "https://www.unieuro.it/online/TV-Neo-QLED/75-Neo-QLED-QN70H-pidSAMQE75QN70H")],
     "Samsung 75\" Neo QLED QN70H 4K 2026", "concorrente", None),
]


CASI_ASIN = [  # (riga ASIN come la manda il sito, anagrafica, titolo Amazon) -> deve essere riconosciuto
    ({"asin": "B0F457M449", "paese": "IT", "modello": "F PRO 32"}, {}, "XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, Smart TV, Fire TV, HD"),
    ({"asin": "B0F457M449", "paese": "IT", "modello": "F PRO 32"},
     {"B0F457M449|IT": {"modello": "F PRO 32", "titolo": "XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, HD"}}, ""),
    ({"asin": "B0F457M449", "paese": "IT"}, {"B0F457M449|IT": {"modello": "F PRO 32", "titolo": ""}},
     "XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, Smart TV, Fire TV, HD"),
]


STRETTO = {"modalita": "stessa_marca", "verifica_url": True, "anno": {"attivo": True, "valore": 2026, "accetta_ignoto": False}}
F75 = "Xiaomi TV F Pro 75 (190 cm), 4K UHD QLED, Smart TV, Fire OS8, HDR10+, MEMC"
OTTO75 = "Xiaomi L75MB-APEU 189 cm (75 Zoll) 4K Ultra HD Smart TV Google TV"
SCHEDE = [  # (titolo ASIN, scheda Amazon, titolo negozio, scheda negozio, parametri, simile?, campo Amazon atteso)
    (F75, {}, OTTO75, {"modelljahr": "2026", "auflösung": "3840 x 2160 Pixel", "bildschirmdiagonale": "189 cm"}, STRETTO, True, None),
    (F75, {}, OTTO75, {"modelljahr": "2025"}, STRETTO, False, None),
    (F75, {}, OTTO75, {}, STRETTO, False, None),                                   # anno sconosciuto ovunque: Stretto scarta
    (F75, {}, OTTO75, {}, {"modalita": "stessa_marca", "verifica_url": True}, True, None),  # Bilanciato: da verificare
    (F75, {}, OTTO75, {"modelljahr": "2026", "auflösung": "1920 x 1080"}, STRETTO, False, None),  # risoluzione diversa
    (F75, {}, OTTO75, {"modelljahr": "2026", "bildschirmdiagonale": "165 cm"}, STRETTO, False, None),  # in realtà un 65"
    (F75, {"anno del modello": "2026"}, OTTO75, {"modelljahr": "2026"}, STRETTO, True, ("anno", 2026)),  # anno ASIN da scheda
    # Otto blocca la pagina prodotto (HTTP 400): il candidato resta; l'anno si cerca su idealo
    (F75, {"_idealo": ["Xiaomi A Pro 75 (2026) 4K QLED"]}, OTTO75, {"_stato": 400}, STRETTO, True, None),
    (F75, {"_idealo": ["Xiaomi A Pro 75 (2025)"]}, OTTO75, {"_stato": 400}, STRETTO, False, None),
    (F75, {}, OTTO75, {"_stato": 400}, STRETTO, False, None),                    # anno introvabile: Stretto scarta
    (F75, {}, OTTO75, {"_stato": 400}, {"modalita": "stessa_marca", "verifica_url": True}, True, None),
    (F75, {}, OTTO75, {"_stato": 404}, {"modalita": "stessa_marca", "verifica_url": True}, False, None),  # prodotto sparito
]


def main():
    errori = 0
    from nucleo import elabora_asin
    import nucleo
    for amz, sch_a, neg, sch, par, atteso, campo in SCHEDE:
        nucleo._ANNI_IDEALO.clear()
        r = elabora_asin(_BrowserFinto(amz, [neg], neg, sch, sch_a), {"asin": "B0TEST0001", "paese": "DE"},
                         [{"nome": "N", "url": "{q}"}], par, log=lambda m: None)
        trovato = bool(r["match"].get("N"))
        if trovato != atteso or (campo and r["amazon"].get(campo[0]) != campo[1]):
            errori += 1
            print(f"✗ scheda tecnica {sch} ({'stretto' if par is STRETTO else 'bilanciato'}): atteso "
                  f"{'simile' if atteso else 'scartato'}, ottenuto {trovato}; {[d['esito'] for d in r['dettaglio']][-2:]}"
                  + (f"; amazon {campo[0]}={r['amazon'].get(campo[0])}" if campo else ""))
    for riga, ana, titolo in CASI_ASIN:
        r = elabora_asin(_BrowserFinto(titolo, ["Xiaomi TV A Pro 32 2026 TV nero"], "Xiaomi - TV A PRO 32 2026 TV, Nero"),
                         dict(riga), [{"nome": "N", "url": "{q}"}], {"modalita": "stessa_marca", "verifica_url": True},
                         log=lambda m: None, anagrafica=ana)
        if r["errore"] or "A PRO 32" not in [m["modello"] for m in r["match"].get("N", [])]:
            errori += 1
            print(f"✗ ASIN con modello {riga.get('modello')!r} / anagrafica {bool(ana)}: errore {r['errore']!r}, "
                  f"amazon {r['amazon'].get('marca')} {r['amazon'].get('pollici')}")
    for amz, ris, tp, modo, atteso in PAGINE:
        r = elabora_asin(_BrowserFinto(amz, ris, tp), {"asin": "B0TEST0000", "paese": "IT"}, [{"nome": "N", "url": "{q}"}],
                         {"modalita": modo, "verifica_url": True}, log=lambda m: None)
        trovati = [m["modello"] for m in r["match"].get("N", [])]
        if (atteso is None and trovati) or (atteso is not None and atteso not in trovati):
            errori += 1
            motivi = [d["esito"] for d in r["dettaglio"]]
            print(f"✗ pagina prodotto ({modo}): {amz[:40]} -> atteso {atteso}, trovati {trovati}; {motivi[-3:]}")
    for titolo, atteso in RICONOSCIMENTO:
        i = analizza(titolo)
        ottenuto = (i.marca, i.tecnologia, i.fascia)
        if ottenuto != atteso:
            errori += 1
            print(f"✗ riconoscimento: {titolo}\n    atteso {atteso}, ottenuto {ottenuto} (chiave {i.chiave!r}, {i.regola})")
    for amz_t, cand_t, modo, atteso in SOMIGLIANZA:
        P = unisci_parametri({"modalita": modo})
        ok, motivo, _ = confronta_param(analizza(amz_t), analizza(cand_t), P)
        if ok != atteso:
            errori += 1
            print(f"✗ somiglianza ({modo}): {amz_t[:45]} ↔ {cand_t[:45]}\n    atteso {'simile' if atteso else 'scartato'}, motivo: {motivo}")
    tot = len(RICONOSCIMENTO) + len(SOMIGLIANZA) + len(PAGINE) + len(CASI_ASIN) + len(SCHEDE)
    print(f"{tot - errori}/{tot} casi corretti")
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
