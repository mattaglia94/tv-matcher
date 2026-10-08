# TV Matcher

Confronta i TV venduti su Amazon (per ASIN) con modelli **simili ma non identici** sui retailer del paese scelto. Il tool non usa AI: si basa solo su regole fisse.

## Requisiti sul PC
- Windows con **Microsoft Edge** (già presente) oppure Google Chrome.
- Nient'altro, se usi `TV_Matcher.exe`.

## Uso mensile
1. Apri `input_tv_matcher.xlsx` e compila il foglio **ASIN** (colonna ASIN e colonna Paese).
   - *Amazon product name* e *Amazon Model* sono facoltativi. Se li compili, il tool non apre Amazon (utile quando Amazon mostra un captcha).
2. Fai doppio click su `TV_Matcher.exe`, scegli il file, il paese e premi **▶ Avvia**.
3. L'output viene salvato nella cartella `Output` con il nome `Matching_TV_<PAESE>_<data>.xlsx`:
   - foglio **Matching**: ASIN, nome e modello Amazon, poi *Model Name* e *Product URL* per ogni retailer. Se non c'è un match valido, le celle restano vuote.
   - foglio **Dettaglio**: tutti i candidati trovati, con il motivo dello scarto oppure "VALIDO". Serve per i controlli di qualità.

Se compare un captcha, spunta "Mostra il browser", risolvilo a mano e il tool riprende da solo.

## Personalizzazione (tutta da Excel, senza toccare il codice)
- Foglio **Retailer**: paese, nome, URL di ricerca (`{q}` = testo cercato), Attivo SI/NO. Si possono aggiungere o disattivare retailer.
- Foglio **Impostazioni**:
  - anno target (2026);
  - se accettare modelli il cui anno non si ricava dal codice (vengono segnalati "anno da verificare");
  - se verificare che ogni URL scelto sia attivo.

## Regole di matching (`app/regole.py`)
Un candidato è valido solo se ha:
- stessa marca e stessi pollici;
- stessa famiglia o fascia (tabelle LG, Hisense e Samsung del documento);
- stessa separazione PRO/non-PRO;
- stessa risoluzione e stessa classe di refresh (se indicate);
- anno pari all'anno target;
- codice diverso da quello Amazon.

Il sistema operativo del TV viene ignorato. Per le altre marche (TCL, Philips…) si applica una regola generica: stessa tecnologia e stessa serie.

Anno dal codice:
- Samsung: lettera finale (H = 2026, F = 2025);
- LG OLED: cifra dopo la serie (C6 = 2026);
- altri: anno indicato nel titolo.

## Creare l'exe (una volta sola)
- **Opzione A**: su un PC Windows con Python installato, doppio click su `build_exe.bat`.
- **Opzione B**: carica la cartella su GitHub. Il workflow `.github/workflows/build.yml` crea l'exe in automatico (scheda Actions → artifact *TV_Matcher*).

## Limiti noti
- I siti cambiano layout e protezioni anti-bot. L'estrazione è generica (legge tutti i link della pagina di ricerca), quindi regge bene, ma se un retailer smette di restituire risultati va controllato il suo URL di ricerca nel foglio Retailer.
- Gli URL di ricerca preimpostati per DE/FR/ES/UK sono ancora da testare.
