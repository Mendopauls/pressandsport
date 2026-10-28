# Press & Sport — Supabase deployment record

Deployment verified 2026-10-28.

- Supabase organization: Press&sport (connected account info@pressandsport.it)
- Project: pressandsport
- Project ref: `acruqsduyucbrkxlqiqi`
- Region: `eu-west-2`
- Schema: `presssport_internal`
- Table: `publication_reservations`
- Migration applied: `presssport_publication_reservations`
- Access: private schema; public/anon/authenticated grants revoked; RLS enabled without public policies
- Security advisor: informational notice about RLS enabled without policy, intentional for private backend-only storage
- Smoke test: duplicate insert inside transaction with rollback; no persistent test records
- Verified ledger count after rollback: 0

## Not yet operational

This is a deployed **database schema**, not a complete cloud publisher. GitHub Actions has not yet been supplied with dedicated backend database credentials. The Meta API publishing workflow and end-to-end idempotency/reconciliation are not implemented. Do not use a publishable/anon key for privileged inserts. Never commit database service-role keys.

## Required go-live safeguards

1. Configure a least-privilege server-side database credential in GitHub Actions secrets (or a dedicated server-side API).
2. Acquire an atomic reservation before any Meta write; duplicate key must fail closed.
3. Validate exact manifest digest and explicit fresh user publication authorization before reservation.
4. Persist attempts and handle uncertain Meta outcomes without automatically retrying.
5. Test concurrent attempts, authorization rejection, Meta failure and reconciliation.
6. Require a separate user authorization for actual Instagram publishing.
