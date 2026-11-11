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
