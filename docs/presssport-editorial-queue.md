# Press & Sport Cloud — reusable editorial queue (phase 1)

This change is the foundation for a user-facing editorial console and a later
separately authorized scheduler. It has **no automatic publishing entrypoint**.

## New post lifecycle

1. Create a new post with a stable `post_key`, caption and 2–10 public JPEG URLs.
   The new row starts in `draft`; no publishing permission is created.
2. Move `draft` → `ready_for_review`. Editing a submitted post requires
   returning it to `draft`, making changes and submitting again.
3. Record named **editorial** approval: `ready_for_review` → `approved`.
   This does not authorize the Instagram API.
4. Optionally save a future editorial plan: `approved` → `planned`.
   A read-only due-date report can identify eligible items, but never publishes.
5. A future production service must obtain a new, separate, explicit publication
   authorization for the exact immutable manifest and Instagram account.
   It must check the existing one-shot reservation ledger before Meta POST.

The existing published carousel dated 28 October is NOT requeued, modified, or
authorized again. The legacy production GitHub workflow remains unchanged and
requires explicit permission.

## Security

- Internal Supabase schema only; Row Level Security enabled and public/anon/
  authenticated table privileges revoked.
- No direct browser access. A future authenticated backend must establish
  operator identity and role server-side; do not trust user-edited JWT metadata.
- The database trigger blocks invalid state changes and content edits after
  submission. Existing published media and reservation ledger are untouched.
- Due-date inspection does not contain Meta credentials, write to the ledger
  or call any Meta publishing endpoints.
- No recurring scheduler is deployed by this phase.

## Operational next step

Add an authenticated editorial console and a release service whose write
authorization is independent of editorial approval. Test a new draft end-to-end
before allowing any scheduled Instagram publications.
