# Press & Sport Cloud V2 — collegamento del pannello

## Stato attuale
Frontend: `admin/editorial-v2.html` + `admin/editorial-v2.js`.
Backend: `scripts/presssport_editorial_authenticated_api.py`.
DB: migration `20261031_presssport_multichannel_queue.sql`.

**Non è ancora un servizio distribuito.** Press & Sport usa GitHub Pages,
che ospita file statici ma non esegue l'API Python. Non usare credenziali
nell'anteprima pubblica del sito.

## Percorso di collegamento
1. Distribuire il backend Python su un runtime server riservato con HTTPS.
2. Mettere il frontend e la rotta `/api/editorial/v2/queue` sulla **stessa origine HTTPS** tramite reverse proxy. La UI non usa CORS cross-origin.
3. Iniettare a deployment `admin/editorial-v2-config.js` con i soli valori pubblici `supabaseUrl`, `publishableKey` e `apiPath`. Il file di esempio non è operativo.
4. Fornire al backend esclusivamente in variabili server `PRESSSPORT_DATABASE_URL`, `PRESSSPORT_SUPABASE_URL`, `PRESSSPORT_SUPABASE_PUBLISHABLE_KEY`.
5. Applicare la migrazione al progetto Supabase verificato `acruqsduyucbrkxlqiqi`, dopo review. Non alterare `publication_reservations` né `editorial_queue` precedenti.
6. Testare: 401 anonimo, 403 utente non autorizzato, 200 amministratore valido, 405 POST, logout e token scaduto.
7. Aggiungere test di integrazione con sessione reale, reverse proxy e configurazione anti-cache prima del deploy di produzione.

Non confondere approvazione editoriale con autorizzazione Meta/LinkedIn.
La console è solo lettura, non ha scheduler né comandi di pubblicazione.
