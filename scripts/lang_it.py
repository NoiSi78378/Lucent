# -*- coding: utf-8 -*-
"""Traduzione italiana aggiuntiva di Lucent.
La traduzione standard è in language/resource.language.it_it/strings.po.
Questo modulo copre i testi Python che non passano dal catalogo Kodi.
"""

STEPS = {
    "welcome": ("Benvenuto",
        "Benvenuto in Lucent! In pochi passaggi configuriamo le funzioni principali: l'add-on video per film e serie, "
        "la chiave TMDb per immagini e informazioni, i canali IPTV, i sottotitoli e la tua videoteca.\n\n"
        "Ogni passaggio mostra lo stato attuale. Puoi saltare ciò che non usi. Per riaprire questa procedura: "
        "Impostazioni > Lucent > Configurazione guidata."),
    "video": ("Film e serie TV",
        "Lucent funziona con qualsiasi add-on video: tieni premuto OK su una cartella dell'add-on e seleziona "
        "«Aggiungi alla home come widget».\n\n"
        "Con l'add-on video del repository Lucent le righe della home si compilano automaticamente e i pulsanti "
        "della scheda informazioni (riproduci, visto, elenchi, trailer e altro) funzionano anche per i titoli di altri add-on."),
    "tmdb": ("Chiave TMDb",
        "TMDb (The Movie Database) fornisce locandine, loghi, cast, studi di produzione e trailer. "
        "Una chiave personale è gratuita e rende il recupero dei dati più rapido e completo.\n\n"
        "Per ottenerla: crea un account su themoviedb.org, quindi apri Impostazioni > API > Crea (uso personale). "
        "Copia la chiave API breve, di 32 caratteri."),
    "iptv": ("TV in diretta (IPTV)",
        "Per la TV in diretta Kodi utilizza IPTV Simple Client. Hai un accesso Xtream (indirizzo server, nome utente e password)? "
        "Premi «Accesso Xtream»: Lucent verifica i dati e configura IPTV Simple, canali, guida e replay. "
        "Se invece hai un collegamento M3U e uno EPG, inseriscili in «Canali e guida».\n\n"
        "Successivamente Lucent mostra guida TV, sezione Sport e risultati in diretta. "
        "Il gruppo preferito compare per primo nella guida; i loghi dei canali possono sostituire quelli del fornitore."),
    "play": ("Immagine e audio",
        "Tre impostazioni per una riproduzione più fluida. Un buffer più grande permette a Kodi di precaricare "
        "una parte maggiore del video e riduce le interruzioni: Lucent sceglie una dimensione adatta alla RAM del dispositivo. "
        "L'adattamento della frequenza al video consente alla TV di passare a 23,976/24 Hz per evitare microscatti "
        "nei movimenti di camera. L'audio passthrough invia Dolby, DTS e Atmos senza modifiche alla soundbar o "
        "all'amplificatore: attivalo soltanto se ne possiedi uno compatibile.\n\n"
        "Su CoreELEC, HDR e Dolby Vision vengono trasmessi automaticamente."),
    "subs": ("Sottotitoli e salta introduzione",
        "Facoltativo. Un add-on video compatibile può cercare sottotitoli nella tua lingua consultando più servizi, "
        "scegliere la lingua parlata, tradurre con l'AI i sottotitoli inglesi e saltare le introduzioni tramite TheIntroDB. "
        "Può funzionare anche con i video provenienti da altri add-on."),
    "library": ("Videoteca",
        "Facoltativo. Un add-on video compatibile può integrare la tua raccolta e i tuoi elenchi Trakt (o Simkl) "
        "nella videoteca Kodi, con schede dei film e delle serie, righe «Continua a guardare» e «Prossimo episodio», "
        "e indicatori dei titoli visti sincronizzati."),
    "tabs": ("Schede",
        "Solis Dashboard (per impianti solari con Solis per Homey) può avere una scheda nella home: mostra "
        "produzione fotovoltaica, consumi della casa, rete elettrica e dati di oggi e del mese. "
        "Premendo OK si apre il pannello completo.\n\n"
        "Puoi aggiungere, spostare o rimuovere altre schede in «Menu e widget»."),
    "look": ("Aspetto",
        "La modalità leggera mantiene Lucent reattiva sui dispositivi con 2 GB di RAM o meno "
        "(meno righe e nessun bagliore delle locandine). Lucent la attiva automaticamente su questi dispositivi. "
        "«Stasera per te» mostra contenuti adatti all'ora del giorno.\n\n"
        "Le locandine grandi sfruttano lo spazio sotto le informazioni; disattivale per usare locandine più piccole "
        "con i titoli. Puoi modificare colori, menu e righe della home in qualsiasi momento dalle impostazioni della skin."),
    "backup": ("Backup",
        "Salva tutte le configurazioni in un unico file: impostazioni e menu di Lucent, preferiti, chiavi (TMDb e AI), "
        "impostazioni degli add-on video, IPTV Simple e sorgenti. Puoi conservarlo su una chiavetta USB o "
        "in una cartella di rete e ripristinarlo dopo una nuova installazione o su un altro dispositivo.\n\n"
        "Il file contiene dati di accesso come Trakt e IPTV: non condividerlo."),
}

TEXT = {
    # Configurazione guidata e relativi stati
    "Set up Lucent": "Configura Lucent",
    "No video add-on for films and series yet": "Nessun add-on video configurato per film e serie",
    "Video add-on: setup assistant": "Add-on video: configurazione guidata",
    "Video add-on settings": "Impostazioni add-on video",
    "Install the video add-on of the Lucent repository": "Installa l'add-on video del repository Lucent",
    "Menu and widgets": "Menu e widget",
    "A TMDb key is set": "Chiave TMDb configurata",
    "No TMDb key yet": "Nessuna chiave TMDb",
    "Enter key": "Inserisci chiave",
    "IPTV Simple Client is switched off": "IPTV Simple Client è disattivato",
    "IPTV Simple Client is not installed (no IPTV? Skip this step)": "IPTV Simple Client non è installato (non usi IPTV? Salta questo passaggio)",
    "No channels yet: fill in your channel list (M3U) and guide (EPG)": "Nessun canale: inserisci l'elenco canali (M3U) e la guida (EPG)",
    "Switch on": "Attiva",
    "Install IPTV Simple Client": "Installa IPTV Simple Client",
    "Xtream login": "Accesso Xtream",
    "Channel list and guide": "Canali e guida TV",
    "none": "nessuno",
    "Channel logos: on": "Loghi canali: attivi",
    "Channel logos: off": "Loghi canali: disattivi",
    "Optional: a video add-on can do subtitles and skip intro": "Facoltativo: un add-on video può gestire sottotitoli e salto introduzione",
    "In your video add-on": "Nel tuo add-on video",
    "Subtitles": "Sottotitoli",
    "Skip intro": "Salta introduzione",
    "Settings": "Impostazioni",
    "Optional: a video add-on can fill Kodi's library": "Facoltativo: un add-on video può riempire la videoteca Kodi",
    "Your video add-on fills the library": "Il tuo add-on video aggiorna la videoteca",
    "Off  ·  switch it on in your video add-on": "Disattivato · attivalo nel tuo add-on video",
    "Choose what goes in the library": "Scegli cosa inserire nella videoteca",
    "Update now": "Aggiorna ora",
    "Light mode on": "Modalità leggera attiva",
    "Light mode off": "Modalità leggera disattivata",
    "Tonight for you on": "Stasera per te attivo",
    "Tonight for you off": "Stasera per te disattivato",
    "big posters": "locandine grandi",
    "small posters": "locandine piccole",
    "Light mode: on": "Modalità leggera: attiva",
    "Light mode: off": "Modalità leggera: disattivata",
    "Big posters: on": "Locandine grandi: attive",
    "Big posters: off": "Locandine grandi: disattivate",
    "Menu and rows": "Menu e righe",
    "frame rate follows the video": "frequenza adattata al video",
    "frame rate fixed": "frequenza fissa",
    "sound to amplifier": "audio all'amplificatore",
    "Kodi decodes the sound": "Kodi decodifica l'audio",
    "Switch on 'frame rate follows the video': without it Dolby Vision shows pink / green":
        "Attiva la frequenza adattata al video: senza, Dolby Vision può apparire rosa o verde",
    "Let the frame rate follow the video (advice)": "Adatta la frequenza al video (consigliato)",
    "Sound to amplifier: on": "Audio all'amplificatore: attivo",
    "Sound to amplifier: off": "Audio all'amplificatore: disattivato",
    "Player settings": "Impostazioni lettore",
    "No backup yet": "Nessun backup",
    "Make a backup": "Crea backup",
    "Restore": "Ripristina",
    "Solis Dashboard has its own tab on Home": "Solis Dashboard ha una scheda nella home",
    "Solis Dashboard is installed but has no tab on Home yet": "Solis Dashboard è installato ma non ha una scheda nella home",
    "The side menu is full. Remove a tab in Menu and widgets first.": "Il menu laterale è pieno. Rimuovi prima una scheda in Menu e widget.",
    "Solis Dashboard tab added": "Aggiunta scheda Solis Dashboard",
    "Add a Solis Dashboard tab": "Aggiungi scheda Solis Dashboard",
    "Back": "Indietro",
    "Finish": "Termina",
    "Start": "Inizia",
    "Next": "Avanti",
    "Set up later": "Configura più tardi",
    "Setup assistant: Settings > Lucent": "Configurazione guidata: Impostazioni > Lucent",
    # Editor menu e widget
    "Menu and widgets": "Menu e widget",
    "+ Add a tab": "+ Aggiungi scheda",
    "Restore the default menu": "Ripristina menu predefinito",
    "Restore the default menu? Your own tabs and widgets will be removed.":
        "Ripristinare il menu predefinito? Le schede e i widget personalizzati saranno rimossi.",
    "{0} widgets": "{0} widget",
    "no widgets (shows the start tab's)": "nessun widget (mostra quelli della scheda iniziale)",
    "start tab": "scheda iniziale",
    "Widgets on this tab": "Widget di questa scheda",
    "Name": "Nome",
    "Icon": "Icona",
    "When clicked": "Quando premi OK",
    "Move up": "Sposta su",
    "Move down": "Sposta giù",
    "Make this the start tab": "Imposta come scheda iniziale",
    "Remove this tab": "Rimuovi scheda",
    "Remove the tab \"{0}\" and its widgets?": "Rimuovere la scheda «{0}» e i suoi widget?",
    "You can have at most {0} tabs.": "Puoi avere al massimo {0} schede.",
    "A tab can have at most {0} widgets.": "Una scheda può contenere al massimo {0} widget.",
    "+ Add a widget": "+ Aggiungi widget",
    "Style": "Stile",
    "Sort": "Ordina",
    "Number of titles": "Numero di titoli",
    "Title picture (instead of the name)": "Immagine del titolo (invece del nome)",
    "Background while in this row": "Sfondo durante la selezione di questa riga",
    "Hide the title of this row": "Nascondi titolo della riga",
    "Show the title of this row again": "Mostra di nuovo il titolo della riga",
    "your own": "personalizzato",
    "none": "nessuno",
    "Choose a picture…": "Scegli un'immagine…",
    "Type an address (http… or a path)…": "Inserisci un indirizzo (http… o percorso)…",
    "No picture of my own": "Nessuna immagine personalizzata",
    "Picture of my own…": "Immagine personalizzata…",
    "Choose the streaming services…": "Scegli i servizi streaming…",
    "Also changed on {0} other tab(s) with the same widget": "Modificato anche su altre {0} schede con lo stesso widget",
    "Posters": "Locandine",
    "Landscape": "Orizzontale",
    "Remove this widget": "Rimuovi widget",
    "Trakt lists (liked or your own)": "Elenchi Trakt (preferiti o personali)",
    "Kodi library": "Videoteca Kodi",
    "Browse an add-on…": "Sfoglia un add-on…",
    "Type a path…": "Inserisci un percorso…",
    "✔ Use this folder: {0}": "✔ Usa questa cartella: {0}",
    "This folder is empty or could not be opened.": "Questa cartella è vuota o non è stato possibile aprirla.",
    "Loading…": "Caricamento…",
    "Show the widgets of this tab": "Mostra i widget di questa scheda",
    "Open a Kodi screen…": "Apri una schermata Kodi…",
    "Open a folder of an add-on…": "Apri una cartella di un add-on…",
    "Start an add-on…": "Avvia un add-on…",
    "Open a favourite…": "Apri un preferito…",
    "Type a Kodi command…": "Inserisci un comando Kodi…",
    "You have no favourites yet.": "Non hai ancora preferiti.",
    "Saved": "Salvato",
    "New tab": "Nuova scheda",
    "Search": "Cerca",
    "Home": "Home",
    "Movies": "Film",
    "TV shows": "Serie TV",
    "Library": "Videoteca",
    "Add-ons": "Add-on",
    "Favourites": "Preferiti",
    "Calendar": "Calendario",
    "Sport": "Sport",
    "TV": "TV",
    "Settings": "Impostazioni",
    "Power": "Spegnimento",
    "Continue watching · Shows": "Continua a guardare · Serie TV",
    "Continue watching · Movies": "Continua a guardare · Film",
    "Trending movies": "Film di tendenza",
    "Trending shows": "Serie di tendenza",
    "Popular movies": "Film popolari",
    "Popular shows": "Serie popolari",
    "Most anticipated movies": "Film più attesi",
    "Most anticipated shows": "Serie più attese",
    "Box office": "Incassi al cinema",
    "Watchlist · Movies": "Da vedere · Film",
    "Watchlist · Shows": "Da vedere · Serie TV",
    "Upcoming episodes": "Prossimi episodi",
    "New shows": "Nuove serie",
    "Recently added movies": "Film aggiunti di recente",
    "Recently added episodes": "Episodi aggiunti di recente",
    "Shows in progress": "Serie iniziate",
    "All movies": "Tutti i film",
    "All shows": "Tutte le serie",
    "Video library": "Videoteca video",
    "Library · Movies": "Videoteca · Film",
    "Library · Shows": "Videoteca · Serie TV",
    "Video files": "File video",
    "Add-on browser": "Gestione add-on",
    "Video add-ons": "Add-on video",
    "Skin settings": "Impostazioni skin",
    "Music": "Musica",
    "Pictures": "Immagini",
    "Power menu": "Menu di spegnimento",
    "Random movies": "Film casuali",
    "Unwatched movies": "Film non visti",
    "Movies in progress": "Film iniziati",
    "Episodes · New and continue": "Episodi · Nuovi e da continuare",
    "Episodes in progress": "Episodi iniziati",
    "Top rated movies": "Film più votati",
    "Random shows": "Serie casuali",
    "Unwatched shows": "Serie non viste",
    "Movie sets": "Saghe cinematografiche",
    "Movie genres": "Generi cinematografici",
    "TV genres": "Generi serie TV",
    "Music videos": "Video musicali",
    "Recently added albums": "Album aggiunti di recente",
    "Recently played albums": "Album ascoltati di recente",
    "Most played albums": "Album più ascoltati",
    "Random albums": "Album casuali",
    "Artists": "Artisti",
    "Video sources": "Sorgenti video",
    "Films · Trending": "Film · Di tendenza",
    "Films · Popular": "Film · Popolari",
    "Films · Top rated": "Film · Più votati",
    "Films · In cinemas": "Film · Al cinema",
    "Films · Coming soon": "Film · Prossimamente",
    "Series · Trending": "Serie · Di tendenza",
    "Series · Popular": "Serie · Popolari",
    "Series · Top rated": "Serie · Più votate",
    "Series · On the air": "Serie · In onda",
    "Series · Coming soon": "Serie · Prossimamente",
    "Series · New": "Serie · Nuove",
    "Continue watching": "Continua a guardare",
    "Continue watching · Films": "Continua a guardare · Film",
    "Continue watching · Episodes": "Continua a guardare · Episodi",
    "Next up": "A seguire",
    "Series · Continue watching and next up": "Serie · Continua a guardare e prossimi episodi",
    "Watchlist · Films": "Da vedere · Film",
    "Watchlist · Series": "Da vedere · Serie",
    "Watchlist · Coming soon": "Da vedere · In arrivo",
    "Collection · Films": "Raccolta · Film",
    "Collection · Series": "Raccolta · Serie",
    "Calendar · New episodes": "Calendario · Nuovi episodi",
    "For you": "Per te",
    "Ready in top quality": "Disponibili in alta qualità",
    "Ready for tonight": "Pronti per stasera",
    "Series · New seasons announced": "Serie · Nuove stagioni annunciate",
    "Films · Oscar: Best Picture": "Film · Oscar al miglior film",
    "Films · Oscar: Best Animated Feature": "Film · Oscar al miglior film d'animazione",
    "Films · Palme d'Or (Cannes)": "Film · Palma d'oro (Cannes)",
    "Series · Emmy: Best Drama": "Serie · Emmy miglior serie drammatica",
    "Series · Emmy: Best Comedy": "Serie · Emmy miglior commedia",
    "No lists found. Log in to Trakt or set your MDBList key or Floppy in your video add-on.":
        "Nessun elenco trovato. Accedi a Trakt o configura la chiave MDBList o Floppy nell'add-on video.",
    "Your lists": "I tuoi elenchi",
    "Name of the actor or actress": "Nome dell'attore o dell'attrice",
    "Lucent needs a TMDb key for this (Skin settings > Integrations).":
        "Per questa funzione serve una chiave TMDb (Impostazioni skin > Integrazioni).",
    "Nobody found with that name": "Nessuna persona trovata con questo nome",
    "Who do you mean?": "Quale persona intendi?",
}


# Altri testi utilizzati dalle finestre di gestione, informazioni e configurazione.
TEXT.update({
    "Glass": "Vetro",
    "White": "Bianco",
    "Crimson": "Cremisi",
    "Emerald": "Smeraldo",
    "Ocean": "Oceano",
    "Violet": "Viola",
    "Amber": "Ambra",
    "Gold": "Oro",
    "Rose": "Rosa",
    "Rose Gold": "Oro rosa",
    "Copper": "Rame",
    "Jade": "Giada",
    "Arctic Blue": "Blu artico",
    "Graphite": "Grafite",
    "Gentle – the screen stays clearly visible": "Leggero: lo schermo rimane ben visibile",
    "Balanced – dark but readable": "Bilanciato: scuro ma leggibile",
    "Strong – barely visible": "Intenso: appena visibile",
    "Off": "Disattivato",
    "On": "Attivo",
    "Home only": "Solo nella home",
    "Show": "Mostra",
    "Dim": "Attenua",
    "Red": "Rosso",
    "Green": "Verde",
    "Blue": "Blu",
    "Small, in the corner": "Piccolo, nell'angolo",
    "Large": "Grande",
    "Small": "Piccolo",
    "check": "spunta",
    "Colour of the check": "Colore della spunta",
    "Size of the check": "Dimensione della spunta",
    "Colour of the check: {0}": "Colore della spunta: {0}",
    "Size of the check: {0}": "Dimensione della spunta: {0}",
    "Watched titles": "Titoli già visti",
    "After 1 second": "Dopo 1 secondo",
    "After 2 seconds": "Dopo 2 secondi",
    "After 3 seconds": "Dopo 3 secondi",
    "After 5 seconds": "Dopo 5 secondi",
    "After 8 seconds": "Dopo 8 secondi",
    "After 10 seconds": "Dopo 10 secondi",
    "After 15 seconds": "Dopo 15 secondi",
    "After 30 seconds": "Dopo 30 secondi",
    "After 1 minute": "Dopo 1 minuto",
    "Never (Back closes it)": "Mai (si chiude con Indietro)",
    "Info first, clean picture after 3 seconds": "Prima informazioni, poi immagine pulita dopo 3 secondi",
    "Info first, clean picture after 5 seconds": "Prima informazioni, poi immagine pulita dopo 5 secondi",
    "Info first, clean picture after 10 seconds": "Prima informazioni, poi immagine pulita dopo 10 secondi",
    "Previous episode": "Episodio precedente",
    "Next episode": "Prossimo episodio",
    "Back 10 seconds": "Indietro di 10 secondi",
    "Forward 30 seconds": "Avanti di 30 secondi",
    "Search subtitles": "Cerca sottotitoli",
    "Info": "Informazioni",
    "Trailer window with soft edge": "Finestra trailer con bordi sfumati",
    "Hero media": "Contenuto in evidenza",
    "Expanded card": "Scheda espansa",
    "Subtle": "Delicato",
    "Balanced": "Bilanciato",
    "Bold": "Intenso",
    "Standard": "Standard",
    "Trakt collection": "Raccolta Trakt",
    "{0} added to your library ({1})": "{0} aggiunto alla tua videoteca ({1})",
    "Trakt · Watchlist": "Trakt · Da vedere",
    "Trakt · {0}": "Trakt · {0}",
    "{0} – choose the lists for this title": "{0} – scegli gli elenchi per questo titolo",
    "Loading your Trakt lists…": "Caricamento degli elenchi Trakt…",
    "Nothing changed": "Nessuna modifica",
    "You are not logged in to Trakt. Log in at Skin settings > Follow > Trakt login.":
        "Non hai effettuato l'accesso a Trakt. Vai a Impostazioni skin > Seguiti > Accesso Trakt.",
    "No video add-on that can play this title. Install a video add-on, or TMDb Helper with a player.":
        "Nessun add-on video può riprodurre questo titolo. Installa un add-on video o TMDb Helper con un lettore.",
    "Trakt does not accept the login any more (Trakt code {0}). Log in again: you get a code that you enter on trakt.tv/activate.":
        "Trakt non accetta più l'accesso (codice {0}). Accedi di nuovo inserendo il codice su trakt.tv/activate.",
    "Log in again now": "Accedi nuovamente",
    "Later": "Più tardi",
    "Trakt did not respond. Try again later.": "Trakt non risponde. Riprova più tardi.",
    "This title has no Trakt or TMDB id.": "Questo titolo non dispone di un ID Trakt o TMDb.",
    "Marked as watched": "Segnato come visto",
    "Marked as not watched": "Segnato come non visto",
    "Director": "Regista",
    "Creator": "Creatore",
    "Born: {0}": "Nascita: {0}",
    "Died: {0}": "Morte: {0}",
    "{0} years": "{0} anni",
    "No TMDB key yet. Enter your own free key in Skin settings > Integrations (or in your video add-on).":
        "Nessuna chiave TMDb. Inserisci una chiave gratuita in Impostazioni skin > Integrazioni (oppure nell'add-on video).",
    "TMDB did not respond. Try again later.": "TMDb non risponde. Riprova più tardi.",
})

def translate(english):
    """Ritorna la traduzione italiana di una stringa fuori dal catalogo Kodi."""
    if english in TEXT:
        return TEXT[english]
    if english.startswith("Step ") and " of " in english:
        return english.replace("Step ", "Passaggio ", 1).replace(" of ", " di ", 1)
    if english.startswith("Your video add-on is installed"):
        return english.replace("Your video add-on is installed", "L'add-on video è installato", 1).replace(
            "account: ", "account: ", 1)
    if english.startswith("Favourite group: "):
        return english.replace("Favourite group: ", "Gruppo preferito: ", 1)
    if english.endswith(" TV channels"):
        return english.replace(" TV channels", " canali TV")
    if english.startswith("Buffer "):
        return english.replace(" (advice ", " (consigliato ").replace("(advice)", "(consigliato)")
    if english.startswith(" (advice "):
        return english.replace(" (advice ", " (consigliato ", 1)
    if english.startswith("Last backup: "):
        return english.replace("Last backup: ", "Ultimo backup: ", 1)
    return english
