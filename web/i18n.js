/* TV Finder — lingua del sito (italiano / inglese).
   Il sito è scritto in italiano; con l'inglese attivo ogni testo mostrato viene tradotto al volo
   (dizionario + frasi con parti variabili). I dati (titoli, modelli, negozi) restano come sono. */
(() => {
  "use strict";
  let L = "it";
  try { L = localStorage.getItem("tvm_lingua") === "en" ? "en" : "it"; } catch { /* memoria non disponibile */ }

  const PAESI = { "Italia": "Italy", "Germania": "Germany", "Francia": "France", "Spagna": "Spain", "Regno Unito": "United Kingdom" };

  const D = {
    // --- generale, menu
    "TV Finder, nuova ricerca": "TV Finder, new search", "Sezioni": "Sections",
    "Nuova ricerca": "New search", "Storico": "History", "Catalogo": "Catalog", "Guida": "Guide", "Feedback": "Feedback",
    "In corso": "Running", "In coda": "Queued", "Coda": "Queued", "Completata": "Completed", "Completato": "Completed",
    "Annullata": "Cancelled", "Interrotta": "Stopped", "Interrotta per errore": "Stopped by an error", "Errore": "Error",
    "In preparazione": "Preparing", "In coda su GitHub": "Queued on GitHub", "Annullamento richiesto": "Cancellation requested",
    "Avviata": "Started", "Avvio": "Start", "Accesso richiesto": "Login required",
    "Password": "Password", "Entra": "Log in",
    "Trova lo stesso modello o i modelli simili alle TV Amazon sui retailer europei.": "Find the same model or similar models to Amazon TVs at European retailers.",
    "Avanti": "Next", "Indietro": "Back", "Inizia": "Start", "Salta": "Skip", "Chiudi": "Close", "Annulla": "Cancel", "Salva": "Save",
    "Elimina": "Delete", "Modifica": "Edit", "Aggiungi": "Add", "Cerca": "Search", "Seleziona": "Select", "Svuota": "Clear",
    "Tutti": "All", "Seleziona tutti": "Select all", "Deseleziona tutti": "Deselect all", "Senza": "Without",
    "facoltativo": "optional", "(facoltativo)": "(optional)", "Esempio:": "Example:", "link": "link", "ricerca": "search",
    "Salvato ✓": "Saved ✓", "Salvo…": "Saving…", "Salva modifiche": "Save changes", "Salva modifiche •": "Save changes •",
    "Configurazione non ancora disponibile": "Configuration not available yet",

    // --- tutorial
    "Benvenuto in TV Finder": "Welcome to TV Finder",
    "Parti da una lista di ASIN Amazon e trova, per ogni retailer europeo, lo stesso modello oppure la TV più simile.": "Start from a list of Amazon ASINs and find, at each European retailer, the same model or the most similar TV.",
    "Incolla gli ASIN": "Paste the ASINs",
    "Copia da Excel, scrivi uno per riga o carica un file. Il paese si legge dalla riga oppure si sceglie per ogni ASIN.": "Copy from Excel, type one per line or upload a file. The country is read from the line or chosen for each ASIN.",
    "Scegli marketplace e criteri": "Choose marketplaces and criteria",
    "Spunta i retailer su cui cercare e decidi quando due TV sono simili: pollici, tecnologia, fascia, anno e altro.": "Tick the retailers to search and decide when two TVs are similar: inches, technology, tier, year and more.",
    "Avvia e chiudi pure": "Start it and feel free to close",
    "La ricerca gira su GitHub: le ricerche grandi si dividono su più macchine in parallelo (100 ASIN in circa 20–30 minuti). Puoi chiudere il browser: la ritrovi nello Storico, con i risultati da scaricare in Excel.": "The search runs on GitHub: large searches are split across several machines in parallel (100 ASINs in about 20–30 minutes). You can close the browser: you will find it in History, with the results to download in Excel.",

    // --- nuova ricerca: passi
    "ASIN": "ASIN", "Incolla o carica la lista": "Paste or upload the list", "Marketplace": "Marketplaces", "Dove cercare": "Where to search",
    "Somiglianza": "Similarity", "Quando due TV sono simili": "When two TVs are similar", "Riepilogo e run": "Summary and run",
    "Parti da una lista di ASIN Amazon: il motore trova, per ogni retailer, lo stesso modello oppure la TV più simile.": "Start from a list of Amazon ASINs: the engine finds, at each retailer, the same model or the most similar TV.",
    "Quali TV vuoi confrontare?": "Which TVs do you want to compare?",
    "Incolla ASIN o link Amazon in qualsiasi formato: uno per riga, separati da virgole o copiati da Excel. Il paese si legge dal link (amazon.de → Germania) o dalla riga, altrimenti vale quello predefinito.": "Paste ASINs or Amazon links in any format: one per line, comma-separated or copied from Excel. The country is read from the link (amazon.de → Germany) or from the line, otherwise the default one applies.",
    "ASIN o link Amazon": "ASINs or Amazon links", "Paese predefinito": "Default country",
    "Incolla qui: B0F457MQCQ, B0F4548TCQ;DE oppure https://www.amazon.it/dp/B0F45BLD1H": "Paste here: B0F457MQCQ, B0F4548TCQ;DE or https://www.amazon.it/dp/B0F45BLD1H",
    "Oppure trascina qui un CSV o un Excel: leggo tutti gli ASIN che contiene": "Or drop a CSV or Excel file here: all the ASINs it contains will be read",
    "Carica file": "Upload file", "Prova con 2 esempi": "Try 2 examples",
    "ASIN da confrontare": "ASINs to compare", "Paese per tutti": "Country for all", "Paese per tutti…": "Country for all…",
    "Cerca ASIN o modello": "Search ASIN or model", "Modello (facoltativo)": "Model (optional)", "Paese": "Country",
    "Il modello è facoltativo: se lo scrivi il motore salta Amazon (utile quando Amazon blocca). I modelli trovati vengono ricordati.": "The model is optional: if you type it, the engine skips Amazon (useful when Amazon blocks). Models found are remembered.",
    "La lista è vuota. Incolla gli ASIN qui accanto, carica un file o prova con gli esempi.": "The list is empty. Paste the ASINs next to it, upload a file or try the examples.",
    "Serve il modello": "Model needed", "Modello a mano (solo se Amazon non basta)": "Manual model (only if Amazon is not enough)", "Letto da Amazon": "Read from Amazon",
    "Nessun ASIN riconosciuto: un ASIN inizia con B0 ed è lungo 10 caratteri.": "No ASIN recognised: an ASIN starts with B0 and is 10 characters long.",
    "Erano già tutti in lista": "They were all already in the list", "Svuotare la lista degli ASIN?": "Clear the ASIN list?",
    "Nessun ASIN corrisponde al filtro.": "No ASIN matches the filter.",
    "Lettore Excel non ancora caricato, riprova tra un secondo": "Excel reader not loaded yet, try again in a second",
    "Scrivi il modello accanto a ogni ASIN evidenziato, poi avvia": "Type the model next to each highlighted ASIN, then start",
    "Impostazioni caricate: controlla e avvia": "Settings loaded: check and start",

    "Su quali marketplace cercare?": "Which marketplaces should be searched?",
    "Ogni ASIN viene cercato sui marketplace attivi del suo paese. Le modifiche valgono per tutti e restano salvate.": "Each ASIN is searched on the active marketplaces of its country. Changes apply to everyone and are saved.",
    "Ripristina originale": "Restore original", "Come scrivere l'URL di ricerca": "How to write the search URL",
    "Apri il sito del retailer, cerca ad esempio": "Open the retailer's website, search for example",
    "e copia l'indirizzo della pagina dei risultati. Poi sostituisci il testo cercato con": "and copy the address of the results page. Then replace the searched text with",
    "Ripristinare l'elenco originale dei marketplace? Le modifiche fatte andranno perse.": "Restore the original list of marketplaces? Your changes will be lost.",
    "Nessun marketplace per questo paese.": "No marketplace for this country.",

    "Tipo di ricerca": "Search type", "Stesso modello": "Same model", "Modello simile": "Similar model",
    "Cerca nei negozi il modello Amazon con il codice identico": "Searches the stores for the Amazon model with the identical code",
    "Cerca un modello simile per caratteristiche, con le regole qui sotto": "Searches for a model with similar features, using the rules below",
    "Cosa cerchi?": "What are you looking for?", "Modalità di ricerca": "Search mode",
    "Alternativa della stessa marca": "Alternative from the same brand",
    "Cerca solo TV della stessa marca dell'ASIN, della stessa famiglia ma con codice diverso.": "Searches only TVs of the ASIN's brand, from the same family but with a different code.",
    "Concorrente equivalente": "Equivalent competitor",
    "Cerca TV di altre marche con stessa diagonale, tecnologia e fascia (es. uno Xiaomi QLED medio → un TCL QLED medio).": "Searches TVs from other brands with the same size, technology and tier (e.g. a mid-range Xiaomi QLED → a mid-range TCL QLED).",
    "Quanto devono essere simili?": "How similar must they be?", "Livello di somiglianza": "Similarity level",
    "Stretto": "Strict", "Bilanciato": "Balanced", "Largo": "Broad",
    "Pochi risultati, molto vicini": "Few results, very close", "Consigliato: le regole del documento": "Recommended: the rules of the document",
    "Più risultati, anche meno simili": "More results, even less similar", "Impostazioni personalizzate": "Custom settings",
    "Personalizza i criteri": "Customise the criteria", "interruttori singoli, preset salvati, opzioni dei risultati": "individual switches, saved presets, result options",
    "Preset salvati": "Saved presets", "Standard (regole del documento)": "Standard (document rules)", "Salva come preset": "Save as preset",
    "Ripristina predefiniti": "Restore defaults", "Nome del preset (es. Largo, Solo stessa marca):": "Preset name (e.g. Broad, Same brand only):",
    "Eliminare il preset?": "Delete the preset?",
    "Schermo": "Screen", "Caratteristiche": "Features", "Risultati": "Results",
    "Pollici": "Inches", "Il modello simile deve avere la stessa diagonale. Con la tolleranza accetti anche diagonali vicine.": "The similar model must have the same screen size. With a tolerance, nearby sizes are accepted too.",
    "Tolleranza ±": "Tolerance ±", "0 = stessa diagonale": "0 = same size",
    "Tecnologia": "Technology", "Tecnologia del pannello": "Panel technology",
    "LED, QLED, Mini-LED, OLED. Le equivalenze rendono intercambiabili due tecnologie (es. Neo QLED Samsung = Mini-LED).": "LED, QLED, Mini-LED, OLED. Equivalences make two technologies interchangeable (e.g. Samsung Neo QLED = Mini-LED).",
    "Considera equivalenti:": "Treat as equivalent:", "Rimuovi equivalenza": "Remove equivalence", "Scegli due tecnologie diverse": "Choose two different technologies",
    "Famiglia": "Family", "famiglia": "family", "Stessa famiglia e fascia": "Same family and tier",
    "Facoltativo: serie con la stessa famiglia sono alternative tra loro": "Optional: series in the same family are alternatives to each other",
    "Famiglie e fasce di ogni marca si vedono e si modificano nel": "Each brand's families and tiers can be viewed and edited in the",
    "Risoluzione": "Resolution", "HD, Full HD, 4K, 8K devono coincidere quando sono indicati su entrambi i prodotti.": "HD, Full HD, 4K, 8K must match when stated on both products.",
    "Frequenza di aggiornamento": "Refresh rate", "Stessa classe: 50/60 Hz, 100/120 Hz, 144 Hz e oltre.": "Same class: 50/60 Hz, 100/120 Hz, 144 Hz and above.",
    "Separazione PRO": "PRO separation", "Un modello PRO si confronta solo con un altro PRO.": "A PRO model is only compared with another PRO.",
    "Solo per le marche che distinguono i modelli PRO": "Only for brands that distinguish PRO models", "Solo PRO": "PRO only",
    "Anno": "Year", "Anno di lancio": "Launch year", "Anno di lancio = Amazon": "Launch year = Amazon", "Stesso della TV Amazon": "Same as the Amazon TV",
    "Anno fisso": "Fixed year", "Se l'anno Amazon non si ricava": "If the Amazon year can't be determined",
    "Accetta i modelli con anno non ricavabile (segnalati \"da verificare\")": "Accept models whose year can't be determined (flagged \"to be checked\")",
    "Dolby Vision": "Dolby Vision", "Se l'ASIN Amazon lo supporta, anche il modello simile deve supportarlo.": "If the Amazon ASIN supports it, the similar model must support it too.",
    "Se l'ASIN Amazon ha HDMI 2.1, anche il modello simile deve averlo.": "If the Amazon ASIN has HDMI 2.1, the similar model must have it too.",
    "Si leggono dalla pagina prodotto: servono la verifica pagina accesa e qualche secondo in più per prodotto.": "Read from the product page: page check must be on, and it takes a few more seconds per product.",
    "Modelli simili da mostrare per ogni marketplace": "Similar models to show for each marketplace", "1, il più vicino": "1, the closest",
    "Fino a 2": "Up to 2", "Fino a 3": "Up to 3",
    "Verifica la pagina prodotto": "Check the product page", "Verifica pagina prodotto": "Check product page",
    "Apre ogni link scelto: controlla che sia attivo e legge anno e caratteristiche. Più lento ma più affidabile.": "Opens each chosen link: checks it is live and reads year and features. Slower but more reliable.",
    "Se un sito blocca la ricerca, usa un comparatore": "If a site blocks the search, use a price comparison site", "Usa idealo come ponte": "Use idealo as a bridge",
    "Cerca il modello simile su idealo (nel Regno Unito su PriceRunner) e tiene solo le offerte di quel retailer. Il risultato è segnalato come trovato tramite servizio terzo.": "Searches for the similar model on idealo (PriceRunner in the UK) and keeps only that retailer's offers. The result is flagged as found via a third-party service.",

    "Tutto pronto": "All set", "Nome della ricerca": "Search name",
    "ASIN nella ricerca": "ASINs in the search", "durata stimata": "estimated duration", "Criteri attivi:": "Active criteria:", "Modalità:": "Mode:",
    "stessa marca": "same brand", "stessa diagonale": "same size", "stesso anno": "same year", "tecnologia": "technology", "pollici": "inches",
    "Avvia la ricerca": "Start the search", "Riusa le impostazioni": "Reuse the settings",
    "Il motore gira su GitHub: puoi chiudere la pagina, cambiare dispositivo o perdere la connessione. Ritrovi la ricerca nello": "The engine runs on GitHub: you can close the page, switch device or lose the connection. You will find the search in",
    "nessun ASIN": "no ASIN",
    "Accendo il motore su GitHub": "Starting the engine on GitHub", "Preparo la configurazione": "Preparing the configuration",
    "Avvio la ricerca…": "Starting the search…", "Ricerca partita!": "Search started!",

    // --- ricerca (risultati)
    "Carico la ricerca…": "Loading the search…", "Ricerca non trovata": "Search not found", "Vai allo storico": "Go to History",
    "Ricerca completata": "Search completed", "Annullare la ricerca? I risultati già trovati restano consultabili.": "Cancel the search? Results already found remain available.",
    "Il motore sta cercando sui siti dei retailer…": "The engine is searching the retailers' websites…",
    "GitHub sta preparando la macchina: di solito serve meno di un minuto. Puoi chiudere la pagina, la ricerca prosegue.": "GitHub is preparing the machine: it usually takes less than a minute. You can close the page, the search continues.",
    "Completa i modelli mancanti": "Fill in the missing models", "Scarica xlsx": "Download xlsx", "Scarica Excel": "Download Excel",
    "ASIN elaborati": "ASINs processed", "modelli simili trovati": "similar models found", "con almeno un modello simile": "with at least one similar model",
    "confronti con esito positivo": "successful comparisons", "Esiti per marketplace": "Outcomes per marketplace", "Registro attività": "Activity log",
    "Filtra per esito": "Filter by outcome", "Con simili": "With similar", "Tutti i marketplace": "All marketplaces", "Vista": "View",
    "Schede": "Cards", "Tabella": "Table", "Modello Amazon": "Amazon model", "Apri su Amazon": "Open on Amazon",
    "Nessun ASIN corrisponde ai filtri.": "No ASIN matches the filters.", "Nessun risultato salvato.": "No saved results.",
    "Saltato": "Skipped", "Trovato": "Found", "Prodotto non presente": "Product not available", "Nessun modello simile": "No similar model",
    "Ricerca non riuscita": "Search failed", "Sito non consultabile": "Site not accessible", "Stesso modello non presente": "Same model not available",
    "Non presente": "Not available", "Nessun simile": "No similar", "Non leggibile": "Not readable", "Da verificare": "To be checked",
    "Nessuna TV con la marca e la diagonale cercate nel catalogo del retailer.": "No TV with the brand and size searched in the retailer's catalogue.",
    "Ci sono TV con la marca e la diagonale cercate, ma nessuno rispetta i criteri.": "There are TVs with the brand and size searched, but none meets the criteria.",
    "Il sito non ha risposto o ha bloccato la ricerca: riprova più tardi.": "The site did not respond or blocked the search: try again later.",
    "La pagina si è aperta ma non mostrava TV leggibili (probabile blocco): verifica a mano.": "The page opened but showed no readable TVs (probably blocked): check manually.",
    "Saltato: serve il modello Amazon": "Skipped: the Amazon model is needed", "In attesa": "Waiting",
    "Modello non riconosciuto": "Model not recognised", "Apri la pagina prodotto": "Open the product page", "Scheda sul comparatore": "Comparison site page",
    "Segnala questo abbinamento": "Report this match", "simile": "similar", "Dal titolo": "From title", "Nessuna (stima dal prezzo)": "None (estimated from price)",
    "Amazon ha bloccato la lettura (captcha): scrivi il modello e rilancia": "Amazon blocked the read (captcha): type the model and run again",
    "Modello ricavato dal web: verificalo": "Model found on the web: check it",
    "Codice non scritto su Amazon: usato il modello a mano": "Code not shown on Amazon: manual model used",
    "Amazon non leggibile: usato il modello a mano": "Amazon not readable: manual model used",
    "Generatore Excel non ancora caricato, riprova": "Excel generator not loaded yet, try again",
    "Fonte": "Source", "Modello trovato": "Model found", "Esito": "Outcome", "Ricerca": "Search", "Dettaglio": "Details", "riferimento": "reference",
    "Nome": "Name", "Modello": "Model", "Data": "Date", "Stato": "Status", "Tipo": "Type", "Negozio": "Store", "Link": "Link", "Note": "Notes",

    // --- storico
    "Tutte le ricerche lanciate dal sito, da qualsiasi dispositivo. Apri una ricerca per vederne risultati o avanzamento.": "All searches launched from the site, from any device. Open a search to see its results or progress.",
    "Seleziona tutte le concluse": "Select all completed", "Elimina selezionate": "Delete selected",
    "Ancora nessuna ricerca": "No searches yet", "Le ricerche avviate compariranno qui, con lo stato e i risultati.": "Searches you start will appear here, with status and results.",
    "Inizia una ricerca": "Start a search", "Una ricerca in corso non si può eliminare": "A running search cannot be deleted",
    "Una ricerca in corso non si può eliminare: annullala prima": "A running search cannot be deleted: cancel it first",
    "Ricerca eliminata": "Search deleted",

    // --- catalogo
    "Marche e serie": "Brands and series", "+ Nuova marca": "+ New brand", "Carico il catalogo…": "Loading the catalog…",
    "Il motore riconosce una TV da marca e serie: qui decidi tecnologia e fascia di ogni serie. Le fasce (Base, Entry, Media, Premium, Top) servono a confrontare marche diverse. Le modifiche valgono per tutte le ricerche successive.": "The engine recognises a TV by brand and series: here you set the technology and tier of each series. Tiers (Base, Entry, Mid, Premium, Top) are used to compare different brands. Changes apply to all following searches.",
    "Prova un titolo": "Try a title", "Titolo da provare": "Title to try",
    "Incolla il nome di una TV come appare su Amazon o su un retailer: vedi subito come viene classificato (anteprima indicativa).": "Paste a TV name as it appears on Amazon or a retailer: see right away how it is classified (indicative preview).",
    "Cerca marca o serie": "Search brand or series", "Cerca nel catalogo": "Search the catalog",
    "Marca non in catalogo: il motore userà la marca indicata da Amazon e stimerà la fascia dal prezzo.": "Brand not in the catalog: the engine will use the brand stated by Amazon and estimate the tier from the price.",
    "Nomi alternativi (separati da virgola)": "Alternative names (comma-separated)", "Fascia se la serie non è in elenco": "Tier if the series is not listed",
    "Tecnologia predefinita": "Default technology", "Serie": "Series", "Descrizione": "Description", "Fascia": "Tier",
    "Inizio del codice serie, es. QN9 vale per QN90…QN94": "Start of the series code, e.g. QN9 covers QN90…QN94",
    "+ Aggiungi serie": "+ Add series", "Elimina serie": "Delete series", "Elimina marca": "Delete brand",
    "Base": "Base", "Entry": "Entry", "Media": "Mid", "Premium": "Premium", "Top": "Top",
    "Fascia Base": "Base tier", "Fascia Entry": "Entry tier", "Fascia Media": "Mid tier", "Fascia Premium": "Premium tier", "Fascia Top": "Top tier",
    "Nessuna marca corrisponde alla ricerca.": "No brand matches the search.", "Nome della marca (es. Bang & Olufsen):": "Brand name (e.g. Bang & Olufsen):",
    "Marca già presente": "Brand already present", "Catalogo salvato: vale dalla prossima ricerca": "Catalog saved: applies from the next search",

    // --- guida
    "Tutto quello che serve per lanciare una ricerca e leggere i risultati.": "Everything you need to launch a search and read the results.",
    "Rivedi il tutorial": "Replay the tutorial", "Inserisci gli ASIN": "Enter the ASINs",
    "Incolla la lista o carica un CSV/Excel. Ogni ASIN ha un paese: lo leggo dalla riga (es.": "Paste the list or upload a CSV/Excel file. Each ASIN has a country: it is read from the line (e.g.",
    ") o uso il paese predefinito. Se Amazon non risponde, scrivi a mano il modello nella colonna facoltativa.": ") or the default country is used. If Amazon doesn't respond, type the model in the optional column.",
    "Scegli i marketplace": "Choose the marketplaces",
    "Spunta i retailer su cui cercare. Puoi modificare un URL, aggiungerne di nuovi o disattivarli: le modifiche valgono per tutti e restano salvate.": "Tick the retailers to search. You can edit a URL, add new ones or disable them: changes apply to everyone and are saved.",
    "Imposta la somiglianza": "Set the similarity",
    "Scegli se cerchi un'alternativa della stessa marca o un concorrente equivalente, poi quanto stretto deve essere il confronto: Stretto, Bilanciato (le regole del documento) o Largo. Per regolare i singoli criteri apri \"Personalizza i criteri\".": "Choose whether you want an alternative from the same brand or an equivalent competitor, then how strict the comparison should be: Strict, Balanced (the document rules) or Broad. To adjust individual criteria open \"Customise the criteria\".",
    "Tieni aggiornato il Catalogo": "Keep the Catalog up to date",
    "Nel Catalogo trovi marche e serie con tecnologia e fascia. Puoi aggiungere una marca, una serie nuova o correggere una fascia: vale dalla ricerca successiva. Con \"Prova un titolo\" vedi subito come viene classificata una TV.": "The Catalog lists brands and series with technology and tier. You can add a brand or a new series, or fix a tier: it applies from the next search. With \"Try a title\" you see right away how a TV is classified.",
    "Avvia e attendi": "Start and wait",
    "Il motore gira su GitHub. Una ricerca da 10 ASIN su 4 retailer richiede circa 10–15 minuti; da 100 ASIN circa 20–30 minuti, perché si divide su più macchine in parallelo. Puoi chiudere la pagina: la pillola verde in alto e lo Storico ti riportano all'avanzamento.": "The engine runs on GitHub. A search of 10 ASINs on 4 retailers takes about 10–15 minutes; 100 ASINs about 20–30 minutes, because it is split across several machines in parallel. You can close the page: the green pill at the top and History take you back to the progress.",
    "Leggi e scarica": "Read and download",
    "Per ogni ASIN vedi i modelli simili per retailer con foto e link. \"Anno da verificare\" segnala i modelli il cui anno non si ricava dal codice. Scarica l'Excel con un foglio per paese più il foglio Dettaglio con tutti i candidati scartati e il motivo.": "For each ASIN you see the similar models per retailer with photo and link. \"Year to be checked\" flags models whose year can't be read from the code. Download the Excel with one sheet per country plus the Details sheet with all discarded candidates and the reason.",
    "Domande frequenti": "Frequently asked questions",
    "Perché un retailer non trova niente?": "Why does a retailer find nothing?",
    "Il sito può aver cambiato l'indirizzo di ricerca o bloccato l'accesso automatico. Controlla l'URL nel passo Marketplace e guarda il foglio Dettaglio: \"ricerca: timeout\" o \"HTTP 403\" indicano un blocco.": "The site may have changed its search address or blocked automated access. Check the URL in the Marketplaces step and look at the Details sheet: \"search: timeout\" or \"HTTP 403\" indicate a block.",
    "Amazon ha bloccato la lettura (captcha): cosa faccio?": "Amazon blocked the read (captcha): what do I do?",
    "Amazon a volte blocca le visite automatiche. Il motore riprova con indirizzi diversi e poi cerca l'ASIN sul web. Se non basta, apri la ricerca, premi \"Completa i modelli mancanti\", scrivi il modello accanto all'ASIN (basta il codice, es. 85U8075F) e avvia. Il modello resta salvato per le ricerche successive.": "Amazon sometimes blocks automated visits. The engine retries with different addresses and then looks up the ASIN on the web. If that isn't enough, open the search, press \"Fill in the missing models\", type the model next to the ASIN (the code is enough, e.g. 85U8075F) and start. The model stays saved for later searches.",
    "Cosa vuol dire \"anno da verificare\"?": "What does \"year to be checked\" mean?",
    "Il codice non dichiara l'anno e il titolo non lo riporta. Il modello rispetta gli altri criteri: verifica l'anno sulla pagina prodotto o spegni \"Accetta anno non ricavabile\".": "The code doesn't state the year and the title doesn't mention it. The model meets the other criteria: check the year on the product page or turn off \"Accept undeterminable year\".",
    "Posso lanciare più ricerche insieme?": "Can I run several searches at once?",
    "Sì, girano in parallelo su GitHub. Ognuna compare nello Storico con il suo stato.": "Yes, they run in parallel on GitHub. Each one appears in History with its status.",
    "Il prezzo viene letto?": "Is the price read?",
    "Solo per le TV che non sono nel Catalogo: se marca o serie sono sconosciute, la fascia viene stimata dal prezzo al pollice e il risultato lo segnala. Per tutti gli altri il confronto si basa su codice modello, pollici e caratteristiche tecniche.": "Only for TVs that aren't in the Catalog: if the brand or series is unknown, the tier is estimated from the price per inch and the result says so. For all others the comparison is based on model code, inches and technical features.",
    "Usa l'intelligenza artificiale?": "Does it use artificial intelligence?",
    "No. Il motore segue regole fisse: legge le pagine dei siti con un browser automatico, riconosce i modelli con il Catalogo (marche, serie, fasce) e confronta le caratteristiche. Nessun servizio di AI viene chiamato.": "No. The engine follows fixed rules: it reads the websites with an automated browser, recognises models using the Catalog (brands, series, tiers) and compares their features. No AI service is called.",
    "Una TV di una marca nuova?": "A TV from a new brand?",
    "Funziona anche senza fare nulla: la marca viene presa da Amazon e la fascia stimata dal prezzo. Per risultati più precisi aggiungi la marca e le sue serie nel": "It works without doing anything: the brand is taken from Amazon and the tier estimated from the price. For more accurate results add the brand and its series in the",

    // --- feedback
    "Segnala un abbinamento sbagliato, un modello mancante o un'idea. I feedback vengono solo raccolti: il tool non cambia finché non vengono valutati.": "Report a wrong match, a missing model or an idea. Feedback is only collected: the tool doesn't change until it has been reviewed.",
    "Nuovo feedback": "New feedback", "Il tuo nome": "Your name", "Cosa non va, o cosa miglioreresti?": "What's wrong, or what would you improve?",
    "Riferimento a una TV": "Reference to a TV", "Invia feedback": "Send feedback",
    "Il testo viene salvato nell'archivio del tool su GitHub, che è pubblico: non scrivere dati personali o riservati.": "The text is saved in the tool's archive on GitHub, which is public: don't write personal or confidential data.",
    "Feedback ricevuti": "Feedback received", "Tutti gli stati": "All statuses", "Tutti i tipi": "All types",
    "Abbinamento errato": "Wrong match", "Modello mancante": "Missing model", "Suggerimento": "Suggestion", "Problema del sito": "Site issue", "Altro": "Other",
    "nuovo": "new", "in valutazione": "under review", "applicato": "applied", "scartato": "rejected",
    "Anonimo": "Anonymous", "Ancora nessun feedback.": "No feedback yet.", "Nessun feedback con questi filtri.": "No feedback with these filters.",
    "Grazie! Feedback inviato": "Thanks! Feedback sent", "Stato aggiornato": "Status updated", "Scrivi il feedback": "Write your feedback",
    "Impostazioni salvate": "Settings saved",

    // --- note del motore
    "altra serie": "other series", "pagina non verificabile": "page could not be checked", "anno da verificare": "year to be checked",
    "tecnologia da verificare": "technology to be checked", "riconosciuto dalle caratteristiche": "recognised from features",
    "modello ricavato da ricerca web: verificare": "model found via web search: to be checked", "modello dalla scheda": "model from the spec sheet",
    "modello non in archivio: dati ricavati dalla pagina Amazon": "model not in the archive: data taken from the Amazon page",
    "codice modello non ricavabile da Amazon: per cercare lo stesso modello scrivilo a mano": "model code not available from Amazon: to search for the same model, type it manually",
    "non sembra una TV (accessorio o ricambio): controlla l'ASIN": "doesn't look like a TV (accessory or spare part): check the ASIN",
    "ricerca web": "web search", "inserito a mano": "entered manually", "anagrafica": "archive", "captcha Amazon": "Amazon captcha", "ok": "ok",
    "Amazon": "Amazon",
    // motivi di scarto (foglio Dettaglio)
    "PRO vs non-PRO": "PRO vs non-PRO", "anno non determinabile": "year not determinable", "codice modello non leggibile": "model code not readable",
    "fascia non determinabile": "tier not determinable", "marca diversa": "different brand", "marca non riconosciuta": "brand not recognised",
    "stessa marca (cerco concorrenti)": "same brand (looking for competitors)", "stesso modello (escluso)": "same model (excluded)",
    "tecnologia non determinabile": "technology not determinable", "URL non attivo": "URL not active",
    "anno non indicato nemmeno nella scheda tecnica": "year not stated even in the spec sheet",
  };

  const P = [];
  const add = (re, f) => P.push([re, f]);
  const tt = (x) => { const r = tr(x); return r == null ? x : r; };
  // bandiere davanti a un testo
  add(/^((?:\p{RI}\p{RI}\s*)+)(.+)$/u, (m, f, x) => { const r = tr(x); return r == null ? null : f + r; });
  add(/^(.+?)((?:\s*\p{RI}\p{RI})+)$/u, (m, x, f) => { const r = tr(x.trim()); return r == null ? null : r + " " + f.trim(); });
  for (const [it, en] of Object.entries(PAESI)) D[it] = en;
  const CRIT = { anno: "year", pollici: "inches", famiglia: "family", tecnologia: "technology", risoluzione: "resolution", refresh: "refresh rate", pro: "PRO", dolby_vision: "Dolby Vision", hdmi21: "HDMI 2.1", hdr10plus: "HDR10+" };
  add(/^Attiva (.+)$/, (m, x) => "Enable " + (CRIT[x] || x));
  add(/^Elimina (.+)$/, (m, x) => "Delete " + x);
  add(/^Rimuovi (.+)$/, (m, x) => "Remove " + x);
  add(/^Seleziona (.+)$/, (m, x) => "Select " + x);
  add(/^Mostra solo (.+)$/, (m, x) => "Show only " + x);
  add(/^Modello di (.+)$/, (m, x) => "Model of " + x);
  add(/^Paese di (.+)$/, (m, x) => "Country of " + x);
  add(/^Tutti i marketplace (.+)$/, (m, x) => "All marketplaces " + tt(x));
  add(/^\+ Aggiungi marketplace in (.+)$/, (m, x) => "+ Add marketplace in " + tt(x));
  add(/^marketplace in (.*)$/, (m, x) => "marketplaces in " + x);
  add(/^ASIN nella ricerca(.*)$/, (m, x) => "ASINs in the search" + x);
  add(/^(\d+)\/(\d+) attivi$/, (m, a, b) => `${a}/${b} active`);
  add(/^(\d+) serie$/, (m, n) => `${n} series`);
  add(/^(\d+) serie · predefinita (.+)$/, (m, n, f) => `${n} series · default ${tt(f)}`);
  add(/^(\d+) marche · (\d+) serie$/, (m, a, b) => `${a} brands · ${b} series`);
  add(/^(\d+) ricerche in corso$/, (m, n) => `${n} searches running`);
  add(/^(\d+) ricerche eliminate$/, (m, n) => `${n} searches deleted`);
  add(/^In corso: (.+)$/, (m, x) => "Running: " + (x === "ricerca" ? "search" : x));
  add(/^(\d+) ASIN aggiunti$/, (m, n) => `${n} ASINs added`);
  add(/^(\d+) parti in parallelo$/, (m, n) => `${n} parts in parallel`);
  add(/^durata stimata · (\d+) parti in parallelo$/, (m, n) => `estimated duration · ${n} parts in parallel`);
  add(/^(\d+)\/(\d+) confronti · (.+)$/, (m, a, b, d) => `${a}/${b} comparisons · ${d}`);
  add(/^(.+) · durata (.+)$/, (m, d, x) => `${d} · duration ${x}`);
  add(/^Avviata (.+)$/, (m, d) => "Started " + d);
  add(/^Già cercato: (.+)$/, (m, x) => "Already searched: " + x);
  add(/^(Trovato|Non presente|Nessun simile|Non leggibile|Saltato|Errore|Da verificare): (\d+)$/, (m, k, n) => `${D[k]}: ${n}`);
  add(/^Marca nuova: (.+) non è nel catalogo$/, (m, x) => `New brand: ${x} is not in the catalog`);
  add(/^Fascia stimata dal prezzo(.*)$/, (m, x) => "Tier estimated from price" + x);
  add(/^Anche: (.*)$/, (m, x) => "Also: " + x);
  add(/^via (.+)$/, (m, x) => "via " + x);
  add(/^Il sito di (.+) non era leggibile: offerta trovata sul comparatore (\S+)(?: \((.+)\))?\. Il link passa da (\S+)\.$/, (m, n, c, p, c2) => `${n}'s website wasn't readable: offer found on the comparison site ${c}${p ? ` (${p})` : ""}. The link goes through ${c2}.`);
  add(/^(.*?) ?Cercato anche su (\S+): nessuna offerta di (.+) per un modello simile\.$/, (m, a, c, n) => `${a ? tt(a) + " " : ""}Also searched on ${c}: no offer from ${n} for a similar model.`);
  add(/^Nessun ASIN trovato in (.+)$/, (m, x) => "No ASIN found in " + x);
  add(/^Nessun marketplace attivo per: (.+)\. Gli ASIN di questi paesi non verranno confrontati\.$/, (m, x) => `No active marketplace for: ${x.split(", ").map(tt).join(", ")}. ASINs from these countries won't be compared.`);
  add(/^Ci sono serie senza codice in: (.+)$/, (m, x) => "Some series have no code in: " + x);
  add(/^(Avvio non riuscito|Impostazioni non salvate|Feedback non inviato|Catalogo non disponibile|Non riesco a leggere le ricerche|Non salvato|Stato non aggiornato): (.*)$/, (m, k, x) => ({
    "Avvio non riuscito": "Start failed", "Impostazioni non salvate": "Settings not saved", "Feedback non inviato": "Feedback not sent",
    "Catalogo non disponibile": "Catalog not available", "Non riesco a leggere le ricerche": "Can't read the searches", "Non salvato": "Not saved",
    "Stato non aggiornato": "Status not updated" }[k]) + ": " + tt(x));
  add(/^(.+): modelli mancanti$/, (m, x) => `${x}: missing models`);
  add(/^Eliminare "(.+)"\? I risultati non saranno più consultabili\.$/, (m, x) => `Delete "${x}"? The results will no longer be available.`);
  add(/^Eliminare (\d+) (ricerca|ricerche) dallo storico\?$/, (m, n, k) => `Delete ${n} ${k === "ricerca" ? "search" : "searches"} from History?`);
  add(/^Eliminare (.+) dal catalogo\? Le sue TV non verranno più riconosciute per serie\.$/, (m, x) => `Delete ${x} from the catalog? Its TVs will no longer be recognised by series.`);
  add(/^Eliminare (.+)\?$/, (m, x) => `Delete ${x}?`);
  add(/^(.+) · serie non in catalogo: uso la fascia predefinita della marca$/, (m, a) => `${a} · series not in the catalog: the brand's default tier is used`);
  add(/^(.+) · serie non riconosciuta: aggiungila qui sotto, oppure il motore stimerà la fascia dal prezzo$/, (m, a) => `${a} · series not recognised: add it below, or the engine will estimate the tier from the price`);
  add(/^(.+) · serie (.+)$/, (m, a, b) => `${a} · series ${b}`);
  // note e motivi del motore
  add(/^trovato tramite (\S+): il sito di (.+) non era leggibile$/, (m, c, n) => `found via ${c}: ${n}'s website wasn't readable`);
  add(/^stessa fascia (\w+)$/, (m, f) => `same tier ${f}`);
  add(/^altra serie, stessa fascia (\w+)$/, (m, f) => `other series, same tier ${f}`);
  add(/^fascia (\w+) \(ASIN (\w+)\)$/, (m, a, b) => `tier ${a} (ASIN ${b})`);
  add(/^fascia (\w+)$/, (m, a) => `tier ${a}`);
  add(/^anno da (\S+)$/, (m, x) => `year from ${x}`);
  add(/^anno nel negozio (.+)$/, (m, x) => `year in store ${x}`);
  add(/^su Amazon (.+)$/, (m, x) => `on Amazon ${x}`);
  add(/^risoluzione (\S+)$/, (m, x) => `resolution ${x}`);
  add(/^tecnologia (\S+)$/, (m, x) => `technology ${x}`);
  add(/^pollici (\S+)$/, (m, x) => `inches ${x}`);
  add(/^anno (\S+)$/, (m, x) => `year ${x}`);
  add(/^anno (\S+) \(da pagina\)$/, (m, x) => `year ${x} (from page)`);
  add(/^anno (\S+) \(tramite (\S+)\)$/, (m, x, d) => `year ${x} (via ${d})`);
  add(/^anno (\S+) letto su (\S+)$/, (m, x, d) => `year ${x} read on ${d}`);
  add(/^famiglia (.+)$/, (m, x) => `family ${x}`);
  add(/^refresh (\S+)$/, (m, x) => `refresh ${x}`);
  add(/^modello diverso \((.+)\)$/, (m, x) => `different model (${x})`);
  add(/^altra serie \((.+), ASIN (.+)\)$/, (m, a, b) => `other series (${a}, ASIN ${b})`);
  add(/^serie diversa e fascia non determinabile \((.+)\)$/, (m, x) => `different series and undeterminable tier (${x})`);
  add(/^la pagina mostra un altro modello \((.+)\)$/, (m, x) => `the page shows a different model (${x})`);
  add(/^scartato: (.+)$/, (m, x) => "rejected: " + tt(x));
  add(/^VALIDO (.+)$/, (m, x) => "VALID " + tt(x));
  add(/^ricerca: (.+)$/, (m, x) => "search: " + x);
  add(/^via (\S+): nessun modello simile tra (\d+) prodotti$/, (m, d, n) => `via ${d}: no similar model among ${n} products`);
  add(/^via (\S+): nessuna offerta (.+) \((\d+) offerte\)$/, (m, d, r, n) => `via ${d}: no ${r} offer (${n} offers)`);
  add(/^pagina prodotto non apribile \((.+)\): uso i dati della ricerca$/, (m, x) => `product page couldn't be opened (${x}): using the search data`);
  add(/^scheda tecnica: (.+) \((\d+) voci\)$/, (m, x, n) => `spec sheet: ${x === "nessun dato utile" ? "no useful data" : x} (${n} entries)`);
  add(/^Amazon \(letto il (.+)\)$/, (m, x) => `Amazon (read on ${x})`);
  add(/^pollici codice (\d+) ≠ titolo (\d+)$/, (m, a, b) => `inches in code ${a} ≠ title ${b}`);
  // registro attività
  add(/^(\d\d:\d\d:\d\d(?: \[\d+\])?\s+)(.+)$/, (m, h, x) => h + tt(x));
  add(/^(.+?): sito non leggibile, provo tramite (\S+)$/, (m, n, c) => `${n}: site not readable, trying via ${c}`);
  add(/^(.+?): (Prodotto non presente|Nessun modello simile|Risultati non leggibili)$/, (m, n, x) => `${n}: ${x === "Risultati non leggibili" ? "Results not readable" : D[x]}`);
  add(/^(.+?): Ricerca non riuscita \((.+)\)$/, (m, n, x) => `${n}: Search failed (${x})`);
  add(/^Browser avviato: (.+)$/, (m, x) => "Browser started: " + x);
  add(/^Motore avviato: (\d+) negozi su (\d+) browser in parallelo$/, (m, a, b) => `Engine started: ${a} stores on ${b} browsers in parallel`);

  const cache = new Map();
  function tr(s) {
    if (s == null) return null;
    s = String(s);
    if (Object.prototype.hasOwnProperty.call(D, s)) return D[s];
    if (cache.has(s)) return cache.get(s);
    let r = null;
    for (const [re, f] of P) {
      const m = s.match(re);
      if (m) { r = f(...m); if (r != null) break; }
    }
    if (r == null) {
      for (const sep of ["; ", ", "]) {
        if (!s.includes(sep)) continue;
        const parti = s.split(sep).map((x) => { const t = tr(x.trim()); return t == null && /[a-zàèéìòù]{3}/.test(x) ? null : (t ?? x); });
        if (parti.every((x) => x != null)) { r = parti.join(sep); break; }
      }
    }
    if (cache.size > 5000) cache.clear();
    cache.set(s, r);
    return r;
  }
  function t(s) { if (L !== "en" || s == null || s === "") return s; const r = tr(String(s).trim()); return r == null ? s : r; }

  // --- traduzione della pagina (solo inglese)
  const fatti = new WeakMap();
  function nodoTesto(n) {
    const v = n.nodeValue;
    if (!v || !/[A-Za-zÀ-ú]/.test(v) || fatti.get(n) === v) return;
    const p = n.parentNode;
    if (!p || p.nodeName === "SCRIPT" || p.nodeName === "STYLE" || p.nodeName === "TEXTAREA" || (p.closest && p.closest("[data-no-trad]"))) return;
    const k = v.trim();
    const r = k.includes("\n") ? k.split("\n").map((x) => tr(x.trim()) ?? x).join("\n") : tr(k);
    if (r != null && r !== k) { const nv = v.replace(k, r); fatti.set(n, nv); n.nodeValue = nv; }
    else fatti.set(n, v);
  }
  const ATTR = ["placeholder", "title", "aria-label"];
  function elemento(el) {
    for (const a of ATTR) {
      const v = el.getAttribute && el.getAttribute(a);
      if (v) { const r = tr(v.trim()); if (r != null && r !== v) el.setAttribute(a, r); }
    }
  }
  function albero(root) {
    if (root.nodeType === 3) return nodoTesto(root);
    if (root.nodeType !== 1) return;
    elemento(root);
    root.querySelectorAll("[placeholder],[title],[aria-label]").forEach(elemento);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) nodoTesto(w.currentNode);
  }
  function avvia() {
    document.documentElement.lang = "en";
    albero(document.body);
    new MutationObserver((ms) => {
      for (const m of ms) {
        if (m.type === "characterData") nodoTesto(m.target);
        else if (m.type === "attributes") elemento(m.target);
        else m.addedNodes.forEach(albero);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTR });
    const c = window.confirm.bind(window), pr = window.prompt.bind(window);
    window.confirm = (msg) => c(t(msg));
    window.prompt = (msg, def) => pr(t(msg), def);
  }

  // --- selettore lingua (IT | EN)
  function selettore() {
    return `<div class="lingua-sel" data-no-trad role="group" aria-label="Lingua / Language">
      <button type="button" data-lingua="it" class="${L === "it" ? "attivo" : ""}" aria-pressed="${L === "it"}">IT</button>
      <button type="button" data-lingua="en" class="${L === "en" ? "attivo" : ""}" aria-pressed="${L === "en"}">EN</button></div>`;
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest && e.target.closest("[data-lingua]");
    if (!b || b.dataset.lingua === L) return;
    try { localStorage.setItem("tvm_lingua", b.dataset.lingua); } catch { /* memoria non disponibile */ }
    location.reload();
  });

  window.I18N = { lingua: L, locale: L === "en" ? "en-GB" : "it-IT", t, selettore, _tr: tr };
  if (L === "en") {
    if (document.body) avvia(); else document.addEventListener("DOMContentLoaded", avvia);
  }
})();
