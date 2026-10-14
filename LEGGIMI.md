# TV Finder

Confronta le TV vendute su Amazon (per ASIN) con modelli **simili ma non identici** sui retailer del paese scelto. Il tool non usa AI: si basa solo su regole fisse.

## Requisiti sul PC
- Windows con **Microsoft Edge** (già presente) oppure Google Chrome.
- Nient'altro, se usi `TV_Finder.exe`.

## Uso mensile
1. Apri `input_tv_matcher.xlsx` e compila il foglio **ASIN** (colonna ASIN e colonna Paese).
   - *Amazon product name* e *Amazon Model* sono facoltativi. Se li compili, il tool non apre Amazon (utile quando Amazon mostra un captcha).
2. Fai doppio click su `TV_Finder.exe`, scegli il file, il paese e premi **▶ Avvia**.
3. L'output viene salvato nella cartella `Output` con il nome `Matching_TV_<PAESE>_<data>.xlsx`:
   - foglio **Matching**: ASIN, nome e modello Amazon, poi *Model Name* e *Product URL* per ogni retailer. Se non c'è un match valido, le celle restano vuote.
   - foglio **Dettaglio**: tutti i candidati trovati, con il motivo dello scarto oppure "VALIDO". Serve per i controlli di qualità.

Se compare un captcha, spunta "Mostra il browser", risolvilo a mano e il tool riprende da solo.

## Personalizzazione (tutta da Excel, senza toccare il codice)
- Foglio **Retailer**: paese, nome, URL di ricerca (`{q}` = testo cercato), Attivo SI/NO. Si possono aggiungere o disattivare retailer.
- Foglio **Impostazioni**:
  - modalità: STESSA MARCA (alternativa della stessa marca) o CONCORRENTE (modello equivalente di un'altra marca);
  - anno target (2026);
  - se accettare modelli il cui anno non si ricava dal codice (vengono segnalati "anno da verificare");
  - se verificare che ogni URL scelto sia attivo.

## Catalogo marche e serie (`web/catalogo.json`)
Ogni marca ha nomi alternativi e un elenco di serie (es. TCL C7, Samsung QN9, LG OLEDC) con tecnologia, fascia
(Base, Entry, Media, Premium, Top) ed eventuale famiglia. Il motore ricava la serie dal codice e la cerca nel catalogo
(vince il prefisso più lungo: QN95 batte QN9).
- Dal sito, scheda **Catalogo**: si aggiungono o modificano marche e serie; le modifiche sono salvate in `config/catalogo.json`
  (branch `dati`) e hanno la precedenza sul catalogo predefinito.
- Con l'exe: un file `catalogo_utente.json` nella cartella del file di input fa lo stesso.
- Marca o serie sconosciute: la marca si prende da Amazon, la tecnologia dal titolo e la fascia si stima dal prezzo al
  pollice (segnalato come "fascia stimata").

Nessuna intelligenza artificiale: solo regole, tabelle e lettura delle pagine con un browser automatico.

## Regole di matching (`app/regole.py`)
Due modalità, scelte per ogni ricerca.

**Alternativa della stessa marca**: un candidato è valido solo se ha
- stessa marca e stessi pollici;
- stessa famiglia (tabelle LG, Hisense e Samsung del documento; tabella `SERIE` per TCL, Philips, Sony, Panasonic; serie Xiaomi);
- stessa separazione PRO/non-PRO;
- stessa risoluzione e stessa classe di refresh (se indicate);
- anno pari all'anno target;
- codice diverso da quello Amazon.

**Concorrente equivalente**: un candidato è valido solo se ha
- marca diversa e stessi pollici;
- stessa tecnologia (con le equivalenze, es. Neo QLED = Mini-LED);
- stessa fascia comune (base, entry, media, premium, top): una fascia di distanza è ammessa ma penalizzata e segnalata;
- stessa risoluzione, classe di refresh e anno, come sopra.

Tra i candidati validi vince quello col punteggio più basso (diagonale e fascia identiche prima di tutto).
Il sistema operativo della TV viene ignorato. Le marche senza tabella (Sharp, Grundig…) usano la serie letterale del codice.

Anno dal codice:
- Samsung: lettera finale (H = 2026, F = 2025);
- LG OLED: cifra dopo la serie (C6 = 2026);
- altri: anno indicato nel titolo.

## Creare l'exe (una volta sola)
- **Opzione A**: su un PC Windows con Python installato, doppio click su `build_exe.bat`.
- **Opzione B**: carica la cartella su GitHub. Il workflow `.github/workflows/build.yml` crea l'exe in automatico (scheda Actions → artifact *TV_Finder*).

## Banco di prova (`app/banco.py`, workflow "Banco di prova")
Serve a verificare il motore su tante TV vere, senza passare dal sito.
- **raccogli**: pesca da Amazon (5 paesi, brand principali, 40–75") TV con la loro scheda tecnica → `banco/asin_<paese>.json` nel branch `dati`.
- **confronta**: lancia il motore completo su un campione di quegli ASIN in tutti i negozi del paese → `runs/banco-…/stato.json`.
- **sonda**: apre pagine di negozi problematici e salva cosa vede il browser.
- In locale: `python app/banco.py valuta <file>` (titolo vs scheda Amazon) e `python app/banco.py esiti <stato.json>` (statistiche per negozio e motivi di scarto).
- `app/banco_campioni.json` (~270 TV reali) è usato da `test_regole.py`: soglie minime di marca, pollici, risoluzione e tecnologia, e nessuna TV vera scambiata per un accessorio.

## Limiti noti
- I siti cambiano layout e protezioni anti-bot. L'estrazione è generica (legge tutti i link della pagina di ricerca), quindi regge bene, ma se un retailer smette di restituire risultati va controllato il suo URL di ricerca.
- Dai server di GitHub alcuni negozi bloccano sempre (AO.com e PCComponentes con Cloudflare, Euronics-DE, Argos spesso) o a volte (Darty, Fnac, Joybuy). Se non sono su idealo, risultano "non leggibili". Dal PC di casa (exe) possono funzionare, perché i blocchi colpiscono soprattutto gli indirizzi dei server.
