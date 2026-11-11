# Press & Sport: Drive import staging

NOT INSTALLED OR DEPLOYED. Nothing in this branch publishes social posts.

Protocol:
- Use a Google Doc located directly in the Press & Sport Drive folder.
- Its filename must start with PS_OLLAMA_READY__.
- First line: PS_OLLAMA_READY=YES.
- The body must contain NON PUBBLICARE; the system creates an unapproved draft.
- The Apps Script scans at most 25 Google Docs per execution, using DriveApp
  and DocumentApp under an authorized account. Only matching files are sent.
- A separate Supabase Edge Function receives the brief over HTTPS, verifies
  the dedicated secret, restricts project_slug to press-sport, and calls only
  existing presssport_worker_enqueue. The existing Mendomate Ollama bridge
  processes pending jobs in the usual way.
- The deduplication key is ps-drive- plus the native Google Drive file ID.
  Existing jobs return HTTP 409. Edits require a new document and new ID.
- No Drive file is made public, and the payload is not sent to social APIs.

Manual activation, not yet performed:
1. Deploy the new presssport-drive-ingest Edge Function separately,
   with verify_jwt=false; the endpoint has its own secret check.
2. Configure PRESSSPORT_DRIVE_INGEST_SECRET in Supabase (random 32+ chars).
3. Create an Apps Script standalone project with the .gs code, setting
   PRESSSPORT_DRIVE_FOLDER_ID, PRESSSPORT_INGEST_URL, and
   PRESSSPORT_DRIVE_INGEST_SECRET as private Script Properties.
   Do not place service_role keys in Apps Script.
4. Run installPressSportDriveIngestTrigger once, grant Google permissions,
   and test with one disposable explicitly marked Google Doc.
5. Verify one pending/completed job, no duplicates, no social publication.

This automation cannot run before the separate function is deployed and
the script owner explicitly authorizes the Google Apps Script trigger.
This uses free-tier products subject to their quotas.


## Stato del collaudo reale, 11 novembre 2026

ATTENZIONE: il documento è stato scritto inizialmente prima del deploy.
Lo stato verificato ora è: nuova Edge Function presssport-drive-ingest
ATTIVA; Apps Script autorizzato manualmente dall'utente, con importazione
di un Google Doc eseguita; Ollama qwen2.5:3b ha prodotto una bozza in
draft_for_review. Il trigger automatico NON è stato verificato e non
deve essere avviato finché la qualità non è sotto controllo.

La prova ha individuato due difetti:
- Instagram 159 caratteri contro minimo 450; LinkedIn 284 contro minimo 650.
- Invenzione di automobile/team di pilotaggio per un brief sui comunicati
  stampa delle società sportive.

Il modulo Python ora include anche validate_grounding ed evaluate_draft:
se il brief contiene la riga Obiettivo:/Tema:/Argomento:, verifica un
minimo di sovrapposizione lessicale dei concetti in entrambe le caption.
È possibile specificare vincoli forti facoltativi:
QA_TOPIC_TERMS: comunicato stampa | società sportiva
QA_FORBIDDEN_TERMS: automobile | pilotaggio

Una verifica lessicale non conferma la correttezza fattuale. La revisione
umana rimane sempre obbligatoria. Il modulo NON è ancora integrato
nel worker Windows esistente: non dichiarare che la generazione reale
sia stata corretta e non riavviare il bridge per questo cambiamento.
