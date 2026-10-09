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
    ("XIAOMI TV F Pro 75,75 pollici (190 cm),4K UHD QLED", "XIAOMI TV F Pro 75 QLED", "stessa_marca", False),  # stesso modello
    ("Hisense 55E7Q 4K QLED 2026", "Hisense 55A7Q QLED 4K 2026", "stessa_marca", True),
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


def main():
    errori = 0
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
    tot = len(RICONOSCIMENTO) + len(SOMIGLIANZA)
    print(f"{tot - errori}/{tot} casi corretti")
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
