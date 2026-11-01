# Press & Sport Cloud V2 — Ollama locale (Windows)

## Stato reale
Il worker `scripts/presssport_ollama_worker.py` è stato scritto e testato offline. **Non è ancora installato sul PC Windows.** Non è ancora collegato alla coda cloud Supabase; il primo collaudo utilizza una cartella locale. Non può pubblicare sui social.

## Meccanismo
- Cartella persistente `%LOCALAPPDATA%\\PressSportOllama\\inbox` per lavori JSON.
- Database SQLite locale `jobs.sqlite3` con chiave univoca per ogni lavoro.
- Lavori interrotti in stato `running` vengono riportati in `pending` al prossimo avvio.
- Bozze generate in `drafts`, con `draft_for_review`: richiedono revisione e non autorizzano pubblicazione.
- Errori ritentati fino a tre tentativi, senza cancellare il brief.
- Installer Task Scheduler per avvio al login Windows (non può lavorare con computer spento).

## Prima installazione
1. Sul PC Windows aprire PowerShell e navigare nella cartella **esatta** `pressandsport\\scripts` che contiene i due file `.ps1` e `presssport_ollama_worker.py` del ramo `feature/presssport-multichannel-editorial-v2`.
2. Eseguire `.\\VERIFICA_PRESSSPORT_OLLAMA.ps1`. Identificare il nome di un modello locale già disponibile.
3. Eseguire `.\\INSTALLA_AVVIO_PRESSSPORT_OLLAMA.ps1 -Model "<modello esistente>"`.
4. Eseguire `Start-ScheduledTask -TaskName PressSport-Ollama-Worker`.
5. Creare un file JSON in `%LOCALAPPDATA%\\PressSportOllama\\inbox\\prova-01.json` contenente `{"job_key":"prova-01","brief":"Proponi una bozza sulla comunicazione delle società sportive senza inventare dati."}`.
6. Verificare `%LOCALAPPDATA%\\PressSportOllama\\drafts\\prova-01.json` e il task Windows.

Il collegamento bidirezionale con Supabase richiederà **credenziali macchina dedicate e a privilegio minimo**, mai la password dell'amministratore nel worker e mai una `service_role` nel PC o repository. Prima di attivarlo occorre creare un'API autenticata per claim/ack dei task e sincronizzazione delle bozze, testata contro i duplicati.

## Sicurezza
Nessun invio a Meta/LinkedIn. Nessuna pubblicazione, revisione o approvazione automatica. Ollama raggiunto solo tramite localhost. Non caricare segreti nel log o nel repository.
