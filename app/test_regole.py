"""Test delle regole di riconoscimento e somiglianza, con titoli reali visti su Amazon e sui retailer.
Uso: python app/test_regole.py   (esce con errore se un caso non torna)
Ogni volta che un risultato sbagliato viene segnalato, il caso va aggiunto qui."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regole import analizza, confronta_param, leggi_prezzo, unisci_parametri  # noqa: E402

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
    ("TCL 43S5L Smart TV QLED FHD 43", ("TCL", "QLED", "BASE")),
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
    ("TV QLED 65 Xiaomi ELA6760EU 4K Fire TV HDR 60 Hz 3HDMI USB", ("XIAOMI", "QLED", "MID")),
    ("TV MiniLED 65 Xiaomi ELA5674EU 4K Google TV Bluetooth 5.2", ("XIAOMI", "MINILED", "PREMIUM")),
    ("TV LED 165cm (65\") XIAOMI F65 ELA6186EU 4K Fire TV Bluetooth 5.0 60Hz", ("XIAOMI", "LED", "ENTRY")),
    ("Bang & Olufsen Beovision Contour 55\" OLED", ("BANG & OLUFSEN", "OLED", "TOP")),
]

# (titolo ASIN, titolo candidato, modalità, deve essere simile?)
# questi casi usano l'anno FISSO 2026 (es. Xiaomi F Pro 2025 -> sostituto A Pro 2026); STESSO_ANNO usa il predefinito
FISSO = {"attivo": True, "modo": "fisso", "valore": 2026, "accetta_ignoto": True}
STESSO_ANNO = [  # predefinito: stesso anno del TV Amazon
    ("Metz 40 Pouces Smart TV FHD QLED 40MQH7000Y", "Metz 40MQF7000Z QLED 40\" Full HD", "stessa_marca", False),  # F = 2025
    # 7000 e 7030 sono modelli diversi (feedback ottobre 2026: "Different model, new model / 2026 energy class")
    ("Metz 40 Pouces Smart TV FHD QLED 40MQH7000Y", "TV QLED 40\" Metz 40MQH7030Z Full HD Smart TV", "stessa_marca", False),
    ("XIAOMI TV F Pro 32 2025, 32 pollici (81 cm), QLED, Smart TV, Fire TV, HD", "Xiaomi TV A Pro 32 2026 TV nero", "stessa_marca", False),
    ("Samsung QE65Q7FAAUXZT QLED 65", "Hisense 65E7Q QLED 65 pollici 4K", "concorrente", True),   # 2025 e 2025
    ("Samsung QE65Q7FAAUXZT QLED 65", "Hisense 65E7S QLED 65 pollici 4K", "concorrente", False),  # 2025 e 2026
]
SOMIGLIANZA = [
    # anno dal codice Hisense (Q = 2025) quando il nome non lo dice (es. idealo): non è un modello 2026
    ("Hisense 65E7DS Smart TV 2026 QLED 65\" 4K", "Hisense 65E7Q QLED 65 pollici 4K", "stessa_marca", False),
    ("Samsung QE65Q7FAAUXZT QLED 65 2025", "Hisense 65E7S QLED 65 pollici 4K", "concorrente", True),
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
    ("Hisense 55E7Q 4K QLED 2026", "Hisense 55A7Q QLED 4K 2026", "stessa_marca", False),  # E7 ≠ A7 (feedback)
    # --- mapping segnalati come errati (feedback ottobre 2026) ---
    ("Hisense 50E7DS PRO Fernseher 50 Zoll, 4K UHD QLED, 144Hz", "Hisense 50Q7S QLED 4K", "stessa_marca", False),  # PRO vs entry
    ("Hisense 65E7DS PRO Fernseher 65 Zoll, 4K UHD QLED, 144Hz", "Hisense 65E7S QLED 4K", "stessa_marca", False),
    ("Hisense Smart TV QLED 144Hz 55\" 4K 55E7S PRO", "Hisense 55E79S QLED 4K", "stessa_marca", False),
    ("Hisense Smart TV MiniLED 165Hz 65\" 4K 65U79S PRO", "Hisense 65Q8S Mini LED 4K", "stessa_marca", False),
    ("Hisense Smart TV 58\" UHD 4K 58E6ST", "Hisense 58A6S 4K UHD", "stessa_marca", False),
    ("Hisense Smart TV QLED 50\" 4K 50A7S", "Hisense 50E7S QLED 4K", "stessa_marca", False),
    ("Hisense 32\" 32A5STUK Hi-QLED Full HD Smart TV", "Hisense 32E5STUK Full HD Smart TV", "stessa_marca", False),
    ("Hisense 50\" 50Q8STUK MiniLED 144Hz 4K", "Hisense 50U7STUK Mini LED 4K", "stessa_marca", False),
    ("TCL 65T8D 65 Pouces QLED avec QD-Mini LED 4K 144 Hz", "TCL 65C79LX1 Mini LED 4K", "stessa_marca", False),  # super entry vs mid
    ("TCL 65T8D 65 Pouces QLED avec QD-Mini LED 4K 144 Hz", "TCL 65C7L SQD Mini LED", "stessa_marca", False),
    ("TCL 65Q7D Pro 65\" SQD-Mini LED TV 4K 144Hz", "TCL 65C6K Pro QD-Mini LED", "stessa_marca", False),
    ("TCL 75Q7D Pro 75\" SQD-Mini LED TV 4K 144Hz", "TCL 75Q7C QD-Mini LED", "stessa_marca", False),       # serie vecchia
    ("Metz QLED TV 55 Zoll 4K 55MQF7500Z", "Metz 55MQF8001Z 4K", "stessa_marca", False),
    ("Metz TV 40 Pulgadas QLED 40MQH7000Y", "Metz 40MTF3001Z LED", "stessa_marca", False),
    ("Samsung Smart TV M1EH 43-Inch, 4K Mini LED [2026] UE43M1EHAU", "Samsung QE43QN70H Neo QLED", "stessa_marca", False),
    ("Samsung Smart TV M1EH 55-Inch, 4K Mini LED [2026] UE55M1EHAU", "Samsung UE55M70H Mini LED", "stessa_marca", False),
    ("Samsung Smart TV M1EH 65-Inch, 4K Mini LED [2026] UE65M1EHAU", "Samsung QE65QN1EH Neo QLED", "stessa_marca", False),
    ("Xiaomi TV F 65 Zoll 2026, 4K UHD, Smart TV, Fire OS8, L65MC-FAEU", "Xiaomi L65MC-AUEU 165 cm (65 Zoll) 4K Ultra HD", "stessa_marca", True),
    ("Xiaomi TV F 65 Zoll 2025, 4K UHD, Smart TV, Fire OS8, L65MB-FAEU", "Xiaomi L65MB-SEU 165 cm (65 Zoll) 4K Mini LED", "stessa_marca", False),
    ("Hisense 55E7Q 4K QLED 2026", "Hisense 55U7Q Mini LED 2026", "stessa_marca", False),  # altra tecnologia
    ("Samsung QE65QN90HATXZT Neo QLED 2026", "Samsung QE65QN92HATXZT Neo QLED 2026", "stessa_marca", True),
    ("LG OLED55C64LA 2026", "LG OLED55C65LA 2026", "stessa_marca", True),
    ("LG OLED55C64LA 2026", "LG OLED55B66LA 2026", "stessa_marca", False),  # fascia diversa
    ("TCL 65C7L SQD Mini LED 2026", "TCL 65C8L SQD Mini LED 2026", "stessa_marca", False),
    # titoli spagnoli senza codice ufficiale: classificati dalle caratteristiche
    ("Xiaomi TV F 65 Pulgadas 2026, 4K UHD Smart TV Fire OS8 HDR10 L65MC-FAEU",
     "TV LED 165cm (65\") Xiaomi ELA7001EU 4K Google TV 2026", "stessa_marca", True),
    ("Xiaomi TV F 65 Pulgadas 2026, 4K UHD Smart TV Fire OS8 HDR10 L65MC-FAEU",
     "TV MiniLED 65 Xiaomi ELA5674EU 4K Google TV 2026", "stessa_marca", False),
    ("Xiaomi TV F 65 Pulgadas 2026, 4K UHD Smart TV Fire OS8 HDR10 L65MC-FAEU",
     "TV LED 165cm (65\") XIAOMI F65 ELA6186EU 4K Fire TV 2026", "stessa_marca", False),       # stesso modello
    ("Xiaomi TV F 65 Pulgadas 2026, 4K UHD Smart TV Fire OS8 L65MC-FAEU", "Hisense 65 pulgadas LED 4K Smart TV 2026 449 €",
     "concorrente", True),
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
        if "idealo" in url:
            nome, pagina = self.sch_a["_idealo"][int(url.rsplit("p", 1)[1])]
            return True, nome, pagina, "", {}
        if self.sch.get("_stato"):  # pagina bloccata dal sito
            return False, "", "", "", {"_stato": self.sch["_stato"]}
        corpo = "Menu: TV 8K OLED, offerte 2025, Classe energetica 2025 © 2025 negozio"
        return True, self.tp, corpo, "", self.sch

    def idealo_cerca(self, dominio, q):
        # _idealo: [(nome prodotto, testo della sua pagina)]
        return [{"url": f"https://www.idealo.de/p{i}", "testo": t[0]} for i, t in enumerate(self.sch_a.get("_idealo", []))]


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
    # titolo della ricerca senza modello (Cdiscount): il modello si legge aprendo l'inserzione
    ("Samsung QE55Q7HAAUXZT QLED 4K 55 pollici 2026", [("Téléviseur QLED 4K noir 55 pouces Samsung", "https://www.cdiscount.com/f-10626-x.html")],
     "Samsung QE55Q6HAAUXZT TV QLED 4K 55\" 2026", "stessa_marca", "QE55Q6HAAUXZT"),
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
    # MediaWorld reale: A Pro 75 a 60 Hz; l'F Pro 75 su Amazon dice "Game Boost 120Hz" (non è la frequenza del pannello)
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED,Smart TV,Fire TV, HDR10+, Modalità Game Boost 120Hz, MEMC", {},
     "Xiaomi A Pro 75 2026 ELA5840EU TV QLED piatto 75 UHD 4K",
     {"frequenza di aggiornamento": "60 Hz", "risoluzione": "3840 x 2160 Pixel"}, {"modalita": "stessa_marca", "verifica_url": True}, True, None),
    (F75, {}, OTTO75, {"modelljahr": "2025"}, STRETTO, False, None),
    (F75, {}, OTTO75, {}, STRETTO, False, None),                                   # anno sconosciuto ovunque: Stretto scarta
    (F75, {}, OTTO75, {}, {"modalita": "stessa_marca", "verifica_url": True}, True, None),  # Bilanciato: da verificare
    (F75, {}, OTTO75, {"modelljahr": "2026", "auflösung": "1920 x 1080"}, STRETTO, False, None),  # risoluzione diversa
    (F75, {}, OTTO75, {"modelljahr": "2026", "bildschirmdiagonale": "165 cm"}, STRETTO, False, None),  # in realtà un 65"
    (F75, {"anno del modello": "2026"}, OTTO75, {"modelljahr": "2026"}, STRETTO, True, ("anno", 2026)),  # anno ASIN da scheda
    # Otto blocca la pagina prodotto (HTTP 400): il candidato resta; l'anno si cerca su idealo
    (F75, {"_idealo": [("Xiaomi A Pro 75 (2025)", "Herstellernummer L75M9-A2EU"),
                       ("Xiaomi A Pro 75 (2026) 4K QLED", "Herstellernummer: L75MB-APEU")]}, OTTO75, {"_stato": 400}, STRETTO, True, None),
    (F75, {"_idealo": [("Xiaomi A Pro 75 (2025)", "Herstellernummer: L75MB-APEU")]}, OTTO75, {"_stato": 400}, STRETTO, False, None),
    # idealo reale: nome "A Pro 75 2026" seguito dalla data di lancio 2025
    (F75, {"_idealo": [("Xiaomi A Pro 75 2026 Xiaomi A Pro 75 2026 4K-Fernseher, 2025, HDR, 3.840 x 2.160",
                        "Zum Shop | Xiaomi L75MB-APEU QLED-Fernseher (189 cm/75 Zoll)")]}, OTTO75, {"_stato": 400}, STRETTO, True, None),
    # stesso nome, ma il codice non compare da nessuna parte: l'anno NON va indovinato
    (F75, {"_idealo": [("Xiaomi A Pro 75 (2025)", "nessun codice"), ("Xiaomi A Pro 75 (2026)", "nessun codice")]},
     OTTO75, {"_stato": 400}, STRETTO, False, None),
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
                         dict(riga), [{"nome": "N", "url": "{q}"}], {"modalita": "stessa_marca", "verifica_url": True, "anno": FISSO},
                         log=lambda m: None, anagrafica=ana)
        if r["errore"] or "A PRO 32" not in [m["modello"] for m in r["match"].get("N", [])]:
            errori += 1
            print(f"✗ ASIN con modello {riga.get('modello')!r} / anagrafica {bool(ana)}: errore {r['errore']!r}, "
                  f"amazon {r['amazon'].get('marca')} {r['amazon'].get('pollici')}")
    for amz, ris, tp, modo, atteso in PAGINE:
        r = elabora_asin(_BrowserFinto(amz, ris, tp), {"asin": "B0TEST0000", "paese": "IT"}, [{"nome": "N", "url": "{q}"}],
                         {"modalita": modo, "verifica_url": True, "anno": FISSO}, log=lambda m: None)
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
        P = unisci_parametri({"modalita": modo, "anno": FISSO})
        ok, motivo, _ = confronta_param(analizza(amz_t), analizza(cand_t, prezzo=leggi_prezzo(cand_t)), P)  # come nel motore
        if ok != atteso:
            errori += 1
            print(f"✗ somiglianza ({modo}): {amz_t[:45]} ↔ {cand_t[:45]}\n    atteso {'simile' if atteso else 'scartato'}, motivo: {motivo}")
    for amz_t, cand_t, modo, atteso in STESSO_ANNO:
        ok, motivo, _ = confronta_param(analizza(amz_t), analizza(cand_t), unisci_parametri({"modalita": modo}))
        if ok != atteso:
            errori += 1
            print(f"✗ stesso anno ({modo}): {amz_t[:45]} ↔ {cand_t[:45]}: atteso {atteso}, motivo {motivo}")
    tot = len(RICONOSCIMENTO) + len(SOMIGLIANZA) + len(PAGINE) + len(CASI_ASIN) + len(SCHEDE) + len(STESSO_ANNO)
    print(f"{tot - errori}/{tot} casi corretti")
    errori += banco_amazon()
    errori += invarianza_modello()
    errori += ponte_uk()
    errori += stesso_modello_test()
    errori += gemelli_test()
    sys.exit(1 if errori else 0)


IDENTICO = [  # modalità "Stesso modello": (titolo Amazon, risultati del negozio, titolo pagina, trovato?)
    # codice IDENTICO: una variante di paese/canale non vale (feedback ottobre 2026)
    ("Samsung QE55Q7FAAUXZT QLED 4K 55 pollici 2025", [("SAMSUNG TV QLED 55\" QE55Q7FAATXZT Smart TV", "https://n.it/p1"),
     ("SAMSUNG TV QLED 55\" QE55Q8FAATXZT", "https://n.it/p2")], "Samsung QE55Q7FAATXZT TV QLED 55", False),
    ("Samsung QE55Q7FAAUXZT QLED 4K 55 pollici 2025", [("SAMSUNG TV QLED 55\" QE55Q7FAAUXZT Smart TV", "https://n.it/p1")],
     "Samsung QE55Q7FAAUXZT TV QLED 55", True),
    ("Hisense 50E7DS PRO Fernseher 50 Zoll QLED", [("Hisense 50E7DS QLED 50 Zoll", "https://n.de/a")], "Hisense 50E7DS", False),
    ("Hisense 50E7DS PRO Fernseher 50 Zoll QLED", [("Hisense 50E7DS PRO QLED 50 Zoll", "https://n.de/b")], "Hisense 50E7DS PRO", True),
    ("Samsung QE55Q7FAAUXZT QLED 4K 55 pollici 2025", [("SAMSUNG TV QLED 55\" QE55Q8FAATXZT", "https://n.it/p2")], "Samsung QE55Q8FAATXZT", False),
    ("LG 55UA73006LA 55 pollici 4K", [("LG UHD 55UA73006LA.AEU Smart TV 55", "https://n.it/x")], "LG 55UA73006LA", True),
    ("Xiaomi TV A Pro 75 2026 QLED", [("Xiaomi TV A Pro 75 2025 QLED", "https://n.it/y")], "Xiaomi TV A Pro 75 2025", True),  # stesso nome, anno diverso: vale (segnalato)
    # caso reale: Amazon "F Pro 43 2025, L43MB-FPEU" = MediaWorld "Xiaomi 43 F PRO 2026" / MediaMarkt "TV F Pro 43 2026"
    ("Xiaomi TV F Pro 43 Pulgadas 2025, 4K UHD QLED Smart Fire TV, L43MB-FPEU", [("TV QLED 43 Xiaomi TV F Pro 43 2026 UHD 4K", "https://n.es/a"),
     ("TV QLED 43 Xiaomi A Pro 2025 43 QLED 4K", "https://n.es/b")], "Xiaomi TV F Pro 43 2026", True),
    ("Xiaomi TV F Pro 43 2025,43 pollici (101 cm), 4K UHD QLED", [("Xiaomi 43 F PRO 2026 Smart TV 43 QLED", "https://n.it/c"),
     ("Xiaomi 32 F PRO 2026 Smart TV 32 QLED HD", "https://n.it/d")], "Xiaomi 43 F PRO 2026", True),
    ("Metz 40 Pouces Smart TV FHD QLED 40MQH7000Y", [("Metz 40MQH7030Z QLED 40", "https://n.it/z")], "Metz 40MQH7030Z", False),
]


def stesso_modello_test():
    from nucleo import elabora_asin
    errori = 0
    for amz, ris, tp, atteso in IDENTICO:
        r = elabora_asin(_BrowserFinto(amz, ris, tp), {"asin": "B0TEST0000", "paese": "IT"}, [{"nome": "N", "url": "{q}"}],
                         {"ricerca": "identico", "verifica_url": True}, log=lambda m: None)
        trovati = [m["modello"] for m in r["match"].get("N", [])]
        if bool(trovati) != atteso:
            errori += 1
            print(f"✗ stesso modello: {amz[:40]} -> trovati {trovati}, atteso {'sì' if atteso else 'no'}")
    print(("✓" if not errori else "✗") + f" stesso modello: {len(IDENTICO) - errori}/{len(IDENTICO)}")
    return errori


def ponte_uk():
    """Regno Unito: sito del negozio bloccato -> si passa da PriceRunner (idealo nel Regno Unito non c'è)."""
    from nucleo import confronta_retailer

    class B:
        visti = []

        def cerca(self, url, q):
            return url, [], "HTTP 403"

        def idealo_cerca(self, dom, q):
            B.visti.append(dom)
            return []

        def pricerunner_cerca(self, q):
            B.visti.append("pricerunner")
            return [{"url": "https://www.pricerunner.com/pl/2-1/TVs/Hisense-65E7S", "testo": "Hisense 65E7S PRO 65\" QLED 4K 2026 £599"}]

        def pricerunner_offerte(self, url):
            return [{"url": "https://clk.klarna.com/uk/gotostore/v1/x", "negozio": "Currys 4.5 (120 ratings)",
                     "testo": "Currys 4.5 Hisense 65E7S £599.00", "prezzo": "£599.00", "img": ""}]

    info = analizza("Samsung QE65Q7HAAUXXU QLED 65 inch 4K 2026")
    P = unisci_parametri({"modalita": "concorrente"})
    r = confronta_retailer(B(), info, {"nome": "Currys", "url": "https://www.currys.co.uk/search?q={q}"}, P, "UK", log=lambda m: None)
    ok = r["esito"].get("Currys") == "trovato" and "pricerunner" in B.visti and not any("idealo" in v for v in B.visti)
    print(("✓" if ok else "✗") + " Regno Unito: ponte PriceRunner" + ("" if ok else f" {r['esito']} {B.visti} {r['dettaglio'][-2:]}"))
    return 0 if ok else 1


def invarianza_modello():
    """Con o senza modello scritto a mano il motore deve vedere lo STESSO TV (stesse caratteristiche, stessi match)."""
    import json
    import os
    from nucleo import prepara_asin
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banco_campioni.json")
    righe = json.load(open(f, encoding="utf-8"))[::4]
    campi = ("marca", "pollici", "tecnologia", "fascia", "famiglia", "risoluzione", "hz", "anno", "pro")
    errori = 0
    P = unisci_parametri({"modalita": "stessa_marca"})
    for r in righe:
        br = _BrowserFinto(r["titolo"], [], "", {}, {})
        base, info0 = prepara_asin(br, {"asin": r["asin"], "paese": r["paese"]}, [], P, log=lambda m: None)
        if info0 is None:
            continue
        for manuale in (info0.codice, info0.codice.lower(), f"{info0.marca} {info0.codice}"):
            out, info = prepara_asin(br, {"asin": r["asin"], "paese": r["paese"], "modello": manuale}, [], P, log=lambda m: None)
            diff = [c for c in campi if info is None or getattr(info, c) != getattr(info0, c)]
            if diff:
                errori += 1
                print(f"✗ modello a mano {manuale!r} cambia {diff}: {r['titolo'][:60]}")
                break
    print(f"{'✓' if not errori else '✗'} modello scritto a mano: nessuna differenza su {len(righe)} TV" if not errori else "")
    return errori


# Banco Amazon: ~280 TV reali (IT/DE/FR/ES/UK, 40-75", brand principali) raccolte da app/banco.py.
# Ciò che il motore capisce dal solo titolo, confrontato con la scheda tecnica Amazon. Soglie minime: non si torna indietro.
SOGLIE_BANCO = {"marca": 99, "pollici": 99, "risoluzione": 97, "tecnologia": 88}  # il resto è rumore delle schede Amazon


def banco_amazon():
    import json
    import os
    from regole import leggi_prezzo
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banco_campioni.json")
    if not os.path.exists(f):
        return 0
    righe = json.load(open(f, encoding="utf-8"))
    ok, tot = {k: 0 for k in SOGLIE_BANCO}, {k: 0 for k in SOGLIE_BANCO}
    for r in righe:
        i = analizza(r["titolo"], prezzo=leggi_prezzo(r.get("prezzo") or ""))
        for k in SOGLIE_BANCO:
            vero = r["scheda"].get(k)
            if not vero:
                continue
            tot[k] += 1
            mio = getattr(i, k)
            ok[k] += mio == vero or (k == "tecnologia" and {mio, vero} <= {"MINILED", "NEOQLED"})
    errori = 0
    from regole import e_accessorio
    falsi = [r["titolo"][:70] for r in righe if e_accessorio(r["titolo"])]
    if falsi:  # nessun TV vero deve essere preso per un accessorio
        errori += 1
        print(f"✗ banco Amazon: {len(falsi)} TV scambiati per accessori, es. {falsi[:3]}")
    for k, soglia in SOGLIE_BANCO.items():
        perc = 100 * ok[k] / (tot[k] or 1)
        segno = "✓" if perc >= soglia else "✗"
        errori += perc < soglia
        print(f"{segno} banco Amazon {k}: {perc:.0f}% su {tot[k]} TV (minimo {soglia}%)")
    return errori


def gemelli_test():
    """MediaMarkt ha trovato il modello, Saturn no: si apre la stessa pagina su saturn.de."""
    from nucleo import completa_gemelli

    class B:
        def __init__(self, titoli):
            self.titoli = titoli

        def verifica(self, url):
            t = self.titoli.get(url)
            return (bool(t), t or "", "", "", {})

        def cerca(self, url, q):
            return url, [], "ok"
    ret = [{"nome": "MediaMarkt", "url": "https://www.mediamarkt.de/de/search.html?query={q}"},
           {"nome": "Saturn", "url": "https://www.saturn.de/de/search.html?query={q}"}]
    base = lambda: {"paese": "DE", "match": {"MediaMarkt": [{"modello": "65E7S", "titolo": "HISENSE 65E7S QLED 65 Zoll",
                    "url": "https://www.mediamarkt.de/de/product/_hisense-65e7s-123456.html", "nota": ""}], "Saturn": []},
                    "esito": {"MediaMarkt": "trovato", "Saturn": "nessun_simile"}, "dettaglio": []}
    o1 = completa_gemelli(B({"https://www.saturn.de/de/product/_hisense-65e7s-123456.html": "HISENSE 65E7S QLED TV | SATURN"}), base(), ret, log=lambda m: None)
    o2 = completa_gemelli(B({"https://www.saturn.de/de/product/_hisense-65e7s-123456.html": "HISENSE 65U7S Mini LED | SATURN"}), base(), ret, log=lambda m: None)
    ok = o1["esito"]["Saturn"] == "trovato" and o1["match"]["Saturn"][0]["url"].startswith("https://www.saturn.de") and o2["esito"]["Saturn"] == "nessun_simile"
    print(("✓" if ok else "✗") + " MediaMarkt / Saturn: controllo incrociato")
    return 0 if ok else 1


if __name__ == "__main__":
    main()
