"""Retailer predefiniti per paese. Sono solo il punto di partenza:
il file di input (foglio "Retailer") li sovrascrive e si possono modificare in Excel.
{q} = testo di ricerca (già codificato per URL)."""

AMAZON_DOMINIO = {"IT": "amazon.it", "DE": "amazon.de", "FR": "amazon.fr",
                  "ES": "amazon.es", "UK": "amazon.co.uk"}

RETAILER = [
    # Paese, Nome, URL ricerca, Attivo
    ("IT", "MediaWorld", "https://www.mediaworld.it/it/search.html?query={q}", "SI"),
    ("IT", "Euronics", "https://www.euronics.it/search?q={q}", "SI"),
    ("IT", "Unieuro", "https://www.unieuro.it/online/?q={q}", "SI"),
    ("IT", "Expert", "https://www.expert.it/it/it/exp/shop/search?terms={q}", "SI"),

    ("ES", "MediaMarkt-ES", "https://www.mediamarkt.es/es/search.html?query={q}", "SI"),
    ("ES", "ElCorteIngles", "https://www.elcorteingles.es/search-nwx/?s={q}", "SI"),
    ("ES", "Carrefour", "https://www.carrefour.es/?q={q}", "SI"),
    ("ES", "PCComponentes", "https://www.pccomponentes.com/search/?query={q}", "SI"),
    ("ES", "Alcampo", "https://www.compraonline.alcampo.es/search?q={q}", "SI"),

    ("DE", "Euronics-DE", "https://www.euronics.de/search?sSearch={q}", "SI"),
    ("DE", "MediaMarkt", "https://www.mediamarkt.de/de/search.html?query={q}", "SI"),
    ("DE", "Saturn", "https://www.saturn.de/de/search.html?query={q}", "SI"),
    ("DE", "Otto", "https://www.otto.de/suche/{q}/", "SI"),
    ("DE", "Joybuy", "https://www.joybuy.de/s?k={q}", "SI"),

    ("UK", "AO.com", "https://ao.com/search?search={q}", "SI"),
    ("UK", "Currys", "https://www.currys.co.uk/search?q={q}", "SI"),
    ("UK", "Very", "https://www.very.co.uk/e/q/{q}.end", "SI"),
    ("UK", "Argos", "https://www.argos.co.uk/search/{q}/", "SI"),
    ("UK", "John Lewis", "https://www.johnlewis.com/search?search-term={q}", "SI"),
    ("UK", "Joybuy", "https://www.joybuy.co.uk/s?k={q}", "SI"),

    ("FR", "Boulanger", "https://www.boulanger.com/resultats?tr={q}", "SI"),
    ("FR", "Conforama", "https://www.conforama.fr/recherche-conforama/{q}", "SI"),
    ("FR", "CarrefourDrive-FR", "https://www.carrefour.fr/s?q={q}", "SI"),
    ("FR", "E.Leclerc-FR", "https://www.e.leclerc/recherche?q={q}", "SI"),
    ("FR", "Auchan", "https://www.auchan.fr/recherche?text={q}", "SI"),
    ("FR", "Darty", "https://www.darty.com/nav/recherche?text={q}", "SI"),
    ("FR", "Cdiscount", "https://www.cdiscount.com/search/10/{q}.html", "SI"),
    ("FR", "Fnac", "https://www.fnac.com/SearchResult/ResultList.aspx?Search={q}", "SI"),
    ("FR", "Joybuy", "https://www.joybuy.fr/s?k={q}", "SI"),
    # negozi online ufficiali dei brand (vendono solo la propria marca)
    ("UK", "Samsung-UK", "https://www.samsung.com/uk/search/?searchvalue={q}", "SI"),
    ("UK", "LG-UK", "https://www.lg.com/uk/search/?search={q}", "SI"),
    ("UK", "Xiaomi-UK", "https://www.mi.com/uk/search/{q20}", "SI"),
    ("DE", "Samsung-DE", "https://www.samsung.com/de/search/?searchvalue={q}", "SI"),
    ("DE", "LG-DE", "https://www.lg.com/de/search/?search={q}", "SI"),
    ("DE", "Hisense-DE", "https://de.hisense.com/search?q={q}", "SI"),
    ("DE", "Xiaomi-DE", "https://www.mi.com/de/search/{q20}", "SI"),
    ("FR", "Samsung-FR", "https://www.samsung.com/fr/search/?searchvalue={q}", "SI"),
    ("FR", "LG-FR", "https://www.lg.com/fr/search/?search={q}", "SI"),
    ("FR", "Hisense-FR", "https://hisense.fr/search?q={q}", "SI"),
    ("FR", "Xiaomi-FR", "https://www.mi.com/fr/search/{q20}", "SI"),
    ("IT", "Samsung-IT", "https://www.samsung.com/it/search/?searchvalue={q}", "SI"),
    ("IT", "LG-IT", "https://www.lg.com/it/search/?search={q}", "SI"),
    ("IT", "Xiaomi-IT", "https://www.mi.com/it/search/{q20}", "SI"),
    ("ES", "Samsung-ES", "https://www.samsung.com/es/search/?searchvalue={q}", "SI"),
    ("ES", "LG-ES", "https://www.lg.com/es/search/?search={q}", "SI"),
    ("ES", "Xiaomi-ES", "https://www.mi.com/es/search/{q20}", "SI"),
]
