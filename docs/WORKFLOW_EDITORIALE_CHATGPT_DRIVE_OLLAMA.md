# Flusso editoriale ufficiale — costo aggiuntivo zero

## Obiettivo
Un'unica piattaforma per Press & Sport, Ninaart, USSA e Paolo Savio. Ogni progetto ha dati, cartelle e canali propri.

## Sequenza obbligatoria
1. **ChatGPT — creazione contenuti**: progettazione e redazione del materiale editoriale, con verifica umana dei fatti, dei diritti e dei materiali. Non assumere la disponibilità automatica di un'API ChatGPT gratuita.
2. **Google Drive — salvataggio**: archiviare contenuti, asset e metadati nella cartella Drive del progetto, conservando gli identificativi dei file e delle revisioni.
3. **Ollama — creazione post**: utilizzare i materiali già salvati su Drive per formattare il post per il canale richiesto e predisporre il pacchetto editoriale.
4. **Approvazione umana**: nessuna pubblicazione senza approvazione esplicita del proprietario del progetto, registrata per la revisione specifica del contenuto e il canale.
5. **Pubblicazione**: il servizio di orchestrazione usa solo le API ufficiali dei social già autorizzati, registra esito, data, ID remoto e possibili errori. Ollama non è di per sé un client di pubblicazione.

## Regole architetturali
- Isolamento rigoroso per progetto in database, cartelle Drive e credenziali social.
- Mantenere bozze e code legacy Press & Sport; migrazioni additive.
- Non introdurre provider LLM a pagamento, API con costo a consumo o nuovi abbonamenti.
- Il motore Ollama attuale è locale su Mendomate. Con il PC spento il processo di Ollama NON può elaborare o pubblicare: la disponibilità 24/7 richiede un esecutore sempre acceso, verificato compatibile con il vincolo di costo zero.
- ChatGPT interattivo e Ollama sono componenti diversi. Il passaggio ChatGPT -> Drive non è automatico se non è stata creata e autorizzata un'integrazione dedicata.
- Pianificare una data nel calendario editoriale NON equivale ad autorizzare la pubblicazione.
- Non pubblicare in autonomia finché mancano approvazione esplicita, autorizzazioni dei canali, controlli dei materiali e test integrati.
- Supabase, GitHub e Drive hanno limiti nei rispettivi piani gratuiti. Zero costi aggiuntivi non significa esecuzione o storage illimitati.

## Stato implementato al 3 novembre 2026
- Console multi-progetto, code separate, bozze manuali e tracce gratuite, calendario ed esportazione locale presenti nel codice.
- Flusso completo automatico ChatGPT -> Drive -> Ollama -> social **non ancora implementato né collaudato**.
- AI cloud commerciale disabilitata; pubblicazioni disabilitate.

## Prossime integrazioni, nell'ordine
1. Collegare ciascun progetto alla propria cartella Drive verificata.
2. Definire un pacchetto editoriale con progetto, file Drive, canale, testo, revisione e stato.
3. Preparare l'adattatore Ollama che legge i pacchetti autorizzati da Drive.
4. Aggiungere lo stato di approvazione per revisione e canale, con audit trail.
5. Collegare singolarmente le API dei social, dopo test e autorizzazioni, con comportamento idempotente.
